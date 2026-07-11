from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_user
from app.models.models import Favorite, Song, User
from app.schemas.schemas import FavoriteCreate, FavoriteResponse

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("", response_model=FavoriteResponse, status_code=201)
async def add_favorite(
    payload: FavoriteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Mark a song as a favorite for the authenticated user."""
    song_result = await db.execute(select(Song).where(Song.id == payload.song_id))
    song = song_result.scalar_one_or_none()
    if song is None:
        raise HTTPException(status_code=404, detail="Song not found")

    favorite = Favorite(user_id=current_user.id, song_id=payload.song_id)
    db.add(favorite)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Song already favorited")

    await db.refresh(favorite, attribute_names=["song"])
    return FavoriteResponse.model_validate(favorite)


@router.get("", response_model=list[FavoriteResponse])
async def list_favorites(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """List all favorited songs for the authenticated user, most recent first."""
    result = await db.execute(
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .options(selectinload(Favorite.song))
        .order_by(Favorite.created_at.desc())
    )
    favorites = result.scalars().all()
    return [FavoriteResponse.model_validate(f) for f in favorites]


@router.delete("/{song_id}", status_code=204)
async def remove_favorite(
    song_id,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """Remove a song from favorites."""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.song_id == song_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(favorite)
    await db.flush()
