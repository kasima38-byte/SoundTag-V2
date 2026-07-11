"""
SoundTag Audio Fingerprinting Engine
=====================================
Implements a Shazam-inspired audio fingerprinting algorithm:

1. Decode audio → mono PCM at fixed sample rate
2. Compute Short-Time Fourier Transform (STFT) → spectrogram
3. Find local maxima (constellation map) in time-frequency space
4. Pair peaks with combinatorial hashing (address hash)
5. Store/match hashes against the database

Each "hash" encodes:
    (freq_anchor, freq_point, time_delta) → 64-bit integer

Matching works by:
    - Generating hashes from the query clip
    - Looking up each hash in the DB
    - Grouping candidate matches by song_id and time_offset delta
    - Scoring by the number of temporally coherent matches
"""

import hashlib
import io
import logging
from dataclasses import dataclass
from typing import Iterator

import librosa
import numpy as np
from scipy.ndimage import maximum_filter
from scipy.ndimage import generate_binary_structure, binary_erosion

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


# ─────────────────────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Peak:
    """A local maximum in the spectrogram."""
    freq_bin: int   # frequency bin index
    time_frame: int # time frame index


@dataclass(frozen=True)
class Fingerprint:
    """One address hash with its time offset."""
    address_hash: int  # 64-bit hash of (f1, f2, dt)
    time_offset: int   # time_frame of the anchor peak (ms approximation)


# ─────────────────────────────────────────────────────────────────────────────
# Audio loading
# ─────────────────────────────────────────────────────────────────────────────

def load_audio(audio_bytes: bytes, target_sr: int = None) -> np.ndarray:
    """
    Decode raw audio bytes (any format librosa supports) into a
    mono float32 array at the configured sample rate.
    """
    sr = target_sr or settings.SAMPLE_RATE
    try:
        y, _ = librosa.load(
            io.BytesIO(audio_bytes),
            sr=sr,
            mono=True,
            dtype=np.float32,
        )
        return y
    except Exception as exc:
        logger.error("Failed to decode audio: %s", exc)
        raise ValueError(f"Unsupported or corrupt audio file: {exc}") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Spectrogram
# ─────────────────────────────────────────────────────────────────────────────

def compute_spectrogram(
    audio: np.ndarray,
    n_fft: int = None,
    hop_length: int = None,
) -> np.ndarray:
    """
    Compute log-power spectrogram.
    Returns shape (freq_bins, time_frames).
    """
    n_fft = n_fft or settings.FFT_WINDOW_SIZE
    hop_length = hop_length or settings.HOP_LENGTH

    stft = librosa.stft(audio, n_fft=n_fft, hop_length=hop_length)
    magnitude = np.abs(stft)
    # Log-power with small epsilon to avoid log(0)
    log_magnitude = librosa.amplitude_to_db(magnitude, ref=np.max)
    return log_magnitude


# ─────────────────────────────────────────────────────────────────────────────
# Peak detection (constellation map)
# ─────────────────────────────────────────────────────────────────────────────

def find_peaks(
    spectrogram: np.ndarray,
    num_peaks: int = None,
    neighborhood_size: int = 20,
) -> list[Peak]:
    """
    Find local maxima in the spectrogram using morphological operations.

    Strategy:
    - Apply a maximum filter with a square neighborhood
    - A point is a peak if it equals the filtered value AND
      is greater than the eroded background (suppresses plateaus)
    - Retain only the top `num_peaks` strongest peaks per time slice
    """
    num_peaks = num_peaks or settings.NUM_PEAKS

    struct = generate_binary_structure(2, 1)
    neighborhood = maximum_filter(spectrogram, size=neighborhood_size)
    local_max = (spectrogram == neighborhood)

    # Suppress background using erosion
    eroded = binary_erosion(spectrogram == spectrogram.min(), structure=struct)
    detected_peaks = local_max ^ eroded  # XOR removes background

    freq_indices, time_indices = np.where(detected_peaks)
    amplitudes = spectrogram[freq_indices, time_indices]

    # Sort by amplitude descending, keep top N per time frame
    order = np.argsort(-amplitudes)
    freq_indices = freq_indices[order]
    time_indices = time_indices[order]

    # Bucket by time frame, keep top num_peaks per frame
    peaks_by_time: dict[int, list[tuple[int, float]]] = {}
    for fi, ti, amp in zip(freq_indices, time_indices, amplitudes[order]):
        bucket = peaks_by_time.setdefault(int(ti), [])
        if len(bucket) < num_peaks:
            bucket.append((int(fi), float(amp)))

    peaks = []
    for ti, freq_amps in peaks_by_time.items():
        for fi, _ in freq_amps:
            peaks.append(Peak(freq_bin=fi, time_frame=ti))

    return peaks


# ─────────────────────────────────────────────────────────────────────────────
# Hash generation (combinatorial)
# ─────────────────────────────────────────────────────────────────────────────

def _pack_hash(f1: int, f2: int, dt: int) -> int:
    """
    Pack three integers into a single 64-bit hash.

    Layout (bits):
        f1:  0–19   (20 bits, max freq bin ~1024 safely)
        f2: 20–39   (20 bits)
        dt: 40–55   (16 bits, max delta ~65535 frames)
    """
    return (f1 & 0xFFFFF) | ((f2 & 0xFFFFF) << 20) | ((dt & 0xFFFF) << 40)


def generate_fingerprints(
    peaks: list[Peak],
    fan_value: int = None,
    min_dt: int = None,
    max_dt: int = None,
    hop_length: int = None,
    sample_rate: int = None,
) -> list[Fingerprint]:
    """
    Create fingerprints by pairing each anchor peak with nearby
    target peaks within a time-delta window (the "fan-out zone").

    Returns a list of Fingerprint objects with:
        - address_hash: encodes (f_anchor, f_target, time_delta)
        - time_offset:  time of anchor peak in milliseconds
    """
    fan_value = fan_value or settings.FAN_VALUE
    min_dt = min_dt if min_dt is not None else settings.MIN_HASH_TIME_DELTA
    max_dt = max_dt or settings.MAX_HASH_TIME_DELTA
    hop_length = hop_length or settings.HOP_LENGTH
    sr = sample_rate or settings.SAMPLE_RATE

    # Frames → ms conversion factor
    ms_per_frame = (hop_length / sr) * 1000

    # Sort peaks by time for efficient pairing
    sorted_peaks = sorted(peaks, key=lambda p: p.time_frame)

    fingerprints = []
    n = len(sorted_peaks)

    for i, anchor in enumerate(sorted_peaks):
        count = 0
        j = i + 1
        while j < n and count < fan_value:
            target = sorted_peaks[j]
            dt = target.time_frame - anchor.time_frame
            if dt < min_dt:
                j += 1
                continue
            if dt > max_dt:
                break

            address_hash = _pack_hash(anchor.freq_bin, target.freq_bin, dt)
            time_offset_ms = int(anchor.time_frame * ms_per_frame)

            fingerprints.append(Fingerprint(
                address_hash=address_hash,
                time_offset=time_offset_ms,
            ))
            count += 1
            j += 1

    return fingerprints


# ─────────────────────────────────────────────────────────────────────────────
# High-level pipeline
# ─────────────────────────────────────────────────────────────────────────────

def fingerprint_audio(audio_bytes: bytes) -> list[Fingerprint]:
    """
    Full pipeline: raw audio bytes → list of Fingerprint objects.
    Used both for ingesting songs and for query recognition.
    """
    audio = load_audio(audio_bytes)
    spectrogram = compute_spectrogram(audio)
    peaks = find_peaks(spectrogram)
    fingerprints = generate_fingerprints(peaks)
    logger.info("Generated %d fingerprints from audio clip", len(fingerprints))
    return fingerprints


def fingerprint_audio_in_chunks(
    audio_bytes: bytes,
    chunk_size: int = 1000,
) -> Iterator[list[Fingerprint]]:
    """
    Generator that yields fingerprints in batches.
    Use for large song files to avoid memory pressure during ingestion.
    """
    all_fps = fingerprint_audio(audio_bytes)
    for i in range(0, len(all_fps), chunk_size):
        yield all_fps[i : i + chunk_size]


# ─────────────────────────────────────────────────────────────────────────────
# Matching / scoring
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MatchCandidate:
    song_id: str
    score: int          # number of temporally coherent hash matches
    confidence: float   # normalized 0–100


def score_matches(
    query_fingerprints: list[Fingerprint],
    db_matches: list[dict],  # [{"song_id": ..., "address_hash": ..., "time_offset": ...}]
) -> list[MatchCandidate]:
    """
    Score candidate songs using temporal coherence.

    For each hash hit, compute:
        delta = db_time_offset - query_time_offset

    Songs where many hashes share the same delta are a genuine match
    (they're all shifted by the same time offset, meaning the song
    starts at that point in the original track).

    Returns candidates sorted by score descending.
    """
    # Build lookup: hash → query time offset
    query_hash_map: dict[int, int] = {
        fp.address_hash: fp.time_offset for fp in query_fingerprints
    }

    # song_id → {delta → count}
    match_map: dict[str, dict[int, int]] = {}

    for row in db_matches:
        song_id = str(row["song_id"])
        addr = row["address_hash"]
        db_offset = row["time_offset"]

        query_offset = query_hash_map.get(addr)
        if query_offset is None:
            continue

        delta = db_offset - query_offset
        song_deltas = match_map.setdefault(song_id, {})
        song_deltas[delta] = song_deltas.get(delta, 0) + 1

    # Score = max count of any single delta per song
    candidates = []
    max_score = 1
    for song_id, deltas in match_map.items():
        score = max(deltas.values())
        max_score = max(max_score, score)
        candidates.append(MatchCandidate(song_id=song_id, score=score, confidence=0.0))

    # Normalize confidence
    total_query = len(query_fingerprints) or 1
    for c in candidates:
        # Confidence considers both absolute score and ratio to query size
        c.confidence = round(min(100.0, (c.score / total_query) * 100 * 3), 2)

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates
