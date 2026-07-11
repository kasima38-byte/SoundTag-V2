import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import User
from app.schemas.schemas import RecognizeResponse, SongResponse
from app.services.recognition import RecognitionService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["recognition"])

MAX_AUDIO_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_CONTENT_TYPES = {
    "audio/webm", "audio/mp4", "audio/mpeg", "audio/wav",
    "audio/x-wav", "audio/ogg", "audio/aac",
}


@router.post("/recognize", response_model=RecognizeResponse)
async def recognize_song(
    request: Request,
    file: UploadFile = File(..., description="5-10 second audio clip"),
    device_os: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Identify a song from a short audio recording.

    Accepts audio in webm, mp4/m4a, mp3, wav, ogg, or aac.
    Works for anonymous users (history won't be attributed) or
    authenticated users (history is saved against their account).
    """
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {file.content_type}",
        )

    audio_bytes = await file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")
    if len(audio_bytes) > MAX_AUDIO_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Audio file too large (max 15MB)")

    client_ip = request.client.host if request.client else None

    service = RecognitionService(db)
    try:
        result = await service.recognize(
            audio_bytes=audio_bytes,
            user_id=current_user.id if current_user else None,
            device_os=device_os,
            ip_address=client_ip,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Recognition failed")
        raise HTTPException(status_code=500, detail="Recognition engine error") from exc

    if not result.matched:
        return RecognizeResponse(
            matched=False,
            confidence=result.confidence,
            processing_ms=result.processing_ms,
            message="No match found. Try moving closer to the audio source.",
        )

    return RecognizeResponse(
        matched=True,
        confidence=result.confidence,
        processing_ms=result.processing_ms,
        song=SongResponse.model_validate(result.song),
    )
