import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.models import AudioFingerprint, Song
from app.schemas.schemas import SongCreate, SongResponse
from app.utils.fingerprint import fingerprint_audio

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/songs", tags=["songs"])


@router.post("", response_model=SongResponse, status_code=201)
async def create_song(
    title: str = Form(...),
    artist: str = Form(...),
    album: str | None = Form(None),
    release_year: int | None = Form(None),
    genre: str | None = Form(None),
    isrc: str | None = Form(None),
    artwork_url: str | None = Form(None),
    spotify_url: str | None = Form(None),
    audio_file: UploadFile = File(..., description="Full-length reference audio for fingerprinting"),
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a new song: store metadata and generate its fingerprint
    index from the full-length reference audio file.

    This is the "training" side of the system — every song that should
    be recognizable must be ingested here first.
    """
    if isrc:
        existing = await db.execute(select(Song).where(Song.isrc == isrc))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Song with this ISRC already exists")

    audio_bytes = await audio_file.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        fingerprints = fingerprint_audio(audio_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    if not fingerprints:
        raise HTTPException(status_code=422, detail="Could not extract fingerprints from audio")

    song = Song(
        title=title,
        artist=artist,
        album=album,
        release_year=release_year,
        genre=genre,
        isrc=isrc,
        artwork_url=artwork_url,
        spotify_url=spotify_url,
        fingerprint_count=len(fingerprints),
    )
    db.add(song)
    await db.flush()  # get song.id

    # Bulk insert fingerprints
    fp_rows = [
        AudioFingerprint(
            song_id=song.id,
            address_hash=fp.address_hash,
            time_offset=fp.time_offset,
        )
        for fp in fingerprints
    ]
    db.add_all(fp_rows)
    await db.flush()

    logger.info("Ingested song '%s' by %s: %d fingerprints", title, artist, len(fingerprints))

    return SongResponse.model_validate(song)


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(song_id: UUID, db: AsyncSession = Depends(get_db)):
    """Retrieve song metadata by ID."""
    result = await db.execute(select(Song).where(Song.id == song_id))
    song = result.scalar_one_or_none()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")
    return SongResponse.model_validate(song)
