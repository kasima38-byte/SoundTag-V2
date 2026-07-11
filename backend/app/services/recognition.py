"""
RecognitionService
==================
Orchestrates the full recognize flow:
1. Receive raw audio bytes from the API
2. Generate fingerprints
3. Look up matching hashes in PostgreSQL
4. Score candidates via temporal coherence
5. Return best match (or no-match)
6. Persist result to recognition_history
"""

import logging
import time
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.models import AudioFingerprint, RecognitionHistory, Song
from app.utils.fingerprint import (
    fingerprint_audio,
    score_matches,
    MatchCandidate,
)

logger = logging.getLogger(__name__)
settings = get_settings()


class RecognitionResult:
    def __init__(
        self,
        matched: bool,
        song: Song | None = None,
        confidence: float = 0.0,
        processing_ms: int = 0,
    ):
        self.matched = matched
        self.song = song
        self.confidence = confidence
        self.processing_ms = processing_ms


class RecognitionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def recognize(
        self,
        audio_bytes: bytes,
        user_id: UUID | None = None,
        device_os: str | None = None,
        ip_address: str | None = None,
    ) -> RecognitionResult:
        start = time.monotonic()

        # 1. Generate fingerprints from the query audio
        try:
            query_fps = fingerprint_audio(audio_bytes)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        if not query_fps:
            return RecognitionResult(matched=False, processing_ms=self._elapsed(start))

        query_hashes = [fp.address_hash for fp in query_fps]

        # 2. Look up matching hashes in the database
        # Chunked IN query to stay within pg parameter limits
        chunk_size = 500
        db_rows = []
        for i in range(0, len(query_hashes), chunk_size):
            chunk = query_hashes[i : i + chunk_size]
            result = await self.db.execute(
                select(
                    AudioFingerprint.song_id,
                    AudioFingerprint.address_hash,
                    AudioFingerprint.time_offset,
                ).where(AudioFingerprint.address_hash.in_(chunk))
            )
            db_rows.extend(result.mappings().all())

        processing_ms = self._elapsed(start)
        logger.info(
            "Hash lookup: %d query hashes → %d DB hits in %dms",
            len(query_hashes),
            len(db_rows),
            processing_ms,
        )

        if not db_rows:
            await self._save_history(
                user_id=user_id,
                song_id=None,
                confidence=0.0,
                matched=False,
                audio_duration_ms=len(audio_bytes) // 176,  # rough estimate
                device_os=device_os,
                ip_address=ip_address,
            )
            return RecognitionResult(matched=False, processing_ms=processing_ms)

        # 3. Score candidates
        candidates: list[MatchCandidate] = score_matches(query_fps, db_rows)

        if not candidates or candidates[0].confidence < settings.CONFIDENCE_THRESHOLD * 100:
            await self._save_history(
                user_id=user_id,
                song_id=None,
                confidence=candidates[0].confidence if candidates else 0.0,
                matched=False,
                audio_duration_ms=None,
                device_os=device_os,
                ip_address=ip_address,
            )
            return RecognitionResult(matched=False, processing_ms=self._elapsed(start))

        best = candidates[0]
        logger.info("Best match: song_id=%s confidence=%.1f", best.song_id, best.confidence)

        # 4. Fetch song details
        song_result = await self.db.execute(
            select(Song).where(Song.id == best.song_id)
        )
        song = song_result.scalar_one_or_none()

        await self._save_history(
            user_id=user_id,
            song_id=UUID(best.song_id) if song else None,
            confidence=best.confidence,
            matched=song is not None,
            audio_duration_ms=None,
            device_os=device_os,
            ip_address=ip_address,
        )

        return RecognitionResult(
            matched=song is not None,
            song=song,
            confidence=best.confidence,
            processing_ms=self._elapsed(start),
        )

    async def _save_history(
        self,
        user_id,
        song_id,
        confidence,
        matched,
        audio_duration_ms,
        device_os,
        ip_address,
    ):
        try:
            record = RecognitionHistory(
                user_id=user_id,
                song_id=song_id,
                confidence=confidence,
                matched=matched,
                audio_duration_ms=audio_duration_ms,
                device_os=device_os,
                ip_address=ip_address,
            )
            self.db.add(record)
            await self.db.flush()
        except Exception as exc:
            logger.warning("Failed to save recognition history: %s", exc)

    @staticmethod
    def _elapsed(start: float) -> int:
        return int((time.monotonic() - start) * 1000)
