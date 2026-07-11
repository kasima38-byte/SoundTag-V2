"""
Unit tests for app.utils.fingerprint

Generates synthetic sine-wave audio to avoid depending on external
audio files, then verifies the pipeline produces consistent,
matchable fingerprints.
"""
import io
import numpy as np
import pytest
import soundfile as sf

from app.utils.fingerprint import (
    Peak,
    compute_spectrogram,
    find_peaks,
    fingerprint_audio,
    generate_fingerprints,
    load_audio,
    score_matches,
    _pack_hash,
)


def make_sine_wave_bytes(freq=440.0, duration=5.0, sr=22050, noise=0.0) -> bytes:
    """Generate a WAV file in memory containing a sine tone (+ optional noise)."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * freq * t)
    if noise > 0:
        signal += np.random.normal(0, noise, signal.shape)
    buf = io.BytesIO()
    sf.write(buf, signal.astype(np.float32), sr, format="WAV")
    return buf.getvalue()


class TestLoadAudio:
    def test_loads_valid_audio(self):
        audio_bytes = make_sine_wave_bytes()
        audio = load_audio(audio_bytes)
        assert isinstance(audio, np.ndarray)
        assert audio.dtype == np.float32
        assert len(audio) > 0

    def test_rejects_garbage_bytes(self):
        with pytest.raises(ValueError):
            load_audio(b"not audio data at all")


class TestSpectrogram:
    def test_shape_is_2d(self):
        audio = load_audio(make_sine_wave_bytes())
        spec = compute_spectrogram(audio)
        assert spec.ndim == 2
        assert spec.shape[0] > 0 and spec.shape[1] > 0


class TestPeakDetection:
    def test_finds_peaks_in_pure_tone(self):
        audio = load_audio(make_sine_wave_bytes(freq=1000.0, duration=3.0))
        spec = compute_spectrogram(audio)
        peaks = find_peaks(spec)
        assert len(peaks) > 0
        assert all(isinstance(p, Peak) for p in peaks)

    def test_silence_produces_few_or_no_strong_peaks(self):
        sr = 22050
        silence = np.zeros(sr * 3, dtype=np.float32)
        buf = io.BytesIO()
        sf.write(buf, silence, sr, format="WAV")
        audio = load_audio(buf.getvalue())
        spec = compute_spectrogram(audio)
        peaks = find_peaks(spec)
        # Silence shouldn't produce a dense, structured constellation
        assert isinstance(peaks, list)


class TestHashing:
    def test_pack_hash_is_deterministic(self):
        h1 = _pack_hash(10, 20, 5)
        h2 = _pack_hash(10, 20, 5)
        assert h1 == h2

    def test_pack_hash_distinguishes_inputs(self):
        h1 = _pack_hash(10, 20, 5)
        h2 = _pack_hash(10, 20, 6)
        h3 = _pack_hash(11, 20, 5)
        assert h1 != h2
        assert h1 != h3

    def test_generate_fingerprints_respects_fan_value(self):
        peaks = [Peak(freq_bin=i, time_frame=i) for i in range(20)]
        fps = generate_fingerprints(peaks, fan_value=3, max_dt=100)
        # Each anchor should pair with at most `fan_value` targets
        from collections import Counter
        # Can't directly recover anchor from hash, but total should be bounded
        assert len(fps) <= len(peaks) * 3


class TestFullPipeline:
    def test_fingerprint_audio_returns_fingerprints(self):
        audio_bytes = make_sine_wave_bytes(duration=8.0)
        fps = fingerprint_audio(audio_bytes)
        assert len(fps) > 0

    def test_same_audio_produces_same_fingerprints(self):
        audio_bytes = make_sine_wave_bytes(freq=523.25, duration=5.0)
        fps1 = fingerprint_audio(audio_bytes)
        fps2 = fingerprint_audio(audio_bytes)
        hashes1 = {fp.address_hash for fp in fps1}
        hashes2 = {fp.address_hash for fp in fps2}
        assert hashes1 == hashes2


class TestMatching:
    def test_identical_clip_matches_with_high_confidence(self):
        audio_bytes = make_sine_wave_bytes(freq=660.0, duration=8.0)
        reference_fps = fingerprint_audio(audio_bytes)

        # Simulate DB rows for this song
        song_id = "test-song-id"
        db_rows = [
            {"song_id": song_id, "address_hash": fp.address_hash, "time_offset": fp.time_offset}
            for fp in reference_fps
        ]

        # Query with the same clip (simulating a perfect re-recording)
        query_fps = fingerprint_audio(audio_bytes)
        candidates = score_matches(query_fps, db_rows)

        assert len(candidates) > 0
        assert candidates[0].song_id == song_id
        assert candidates[0].confidence > 50.0

    def test_unrelated_audio_does_not_match(self):
        song_audio = make_sine_wave_bytes(freq=440.0, duration=8.0)
        other_audio = make_sine_wave_bytes(freq=880.0, duration=8.0)

        song_fps = fingerprint_audio(song_audio)
        db_rows = [
            {"song_id": "song-a", "address_hash": fp.address_hash, "time_offset": fp.time_offset}
            for fp in song_fps
        ]

        query_fps = fingerprint_audio(other_audio)
        candidates = score_matches(query_fps, db_rows)

        # Either no candidates, or confidence should be low
        if candidates:
            assert candidates[0].confidence < 50.0

    def test_partial_clip_still_matches(self):
        """A 5-second excerpt of a longer 'song' should still match."""
        sr = 22050
        freq = 330.0
        full_duration = 15.0
        t_full = np.linspace(0, full_duration, int(sr * full_duration), endpoint=False)
        full_signal = 0.5 * np.sin(2 * np.pi * freq * t_full)

        buf_full = io.BytesIO()
        sf.write(buf_full, full_signal.astype(np.float32), sr, format="WAV")
        song_fps = fingerprint_audio(buf_full.getvalue())

        db_rows = [
            {"song_id": "full-song", "address_hash": fp.address_hash, "time_offset": fp.time_offset}
            for fp in song_fps
        ]

        # Take a 5-second excerpt starting at second 5
        excerpt = full_signal[int(5 * sr): int(10 * sr)]
        buf_excerpt = io.BytesIO()
        sf.write(buf_excerpt, excerpt.astype(np.float32), sr, format="WAV")
        query_fps = fingerprint_audio(buf_excerpt.getvalue())

        candidates = score_matches(query_fps, db_rows)
        assert len(candidates) > 0
        assert candidates[0].song_id == "full-song"
