from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# ─────────────────────────────────────────────────────────────
# Songs
# ─────────────────────────────────────────────────────────────

class SongBase(BaseModel):
    title: str
    artist: str
    album: Optional[str] = None
    release_year: Optional[int] = None
    duration_ms: Optional[int] = None
    genre: Optional[str] = None
    isrc: Optional[str] = None
    artwork_url: Optional[str] = None
    spotify_url: Optional[str] = None
    apple_music_url: Optional[str] = None
    youtube_url: Optional[str] = None


class SongCreate(SongBase):
    pass


class SongResponse(SongBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    fingerprint_count: int
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# Recognition
# ─────────────────────────────────────────────────────────────

class RecognizeResponse(BaseModel):
    matched: bool
    confidence: float = 0.0
    processing_ms: int = 0
    song: Optional[SongResponse] = None
    message: Optional[str] = None


# ─────────────────────────────────────────────────────────────
# History
# ─────────────────────────────────────────────────────────────

class HistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    song: Optional[SongResponse] = None
    confidence: Optional[float]
    matched: bool
    recognized_at: datetime


class HistoryListResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int


# ─────────────────────────────────────────────────────────────
# Favorites
# ─────────────────────────────────────────────────────────────

class FavoriteCreate(BaseModel):
    song_id: UUID


class FavoriteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    song: SongResponse
    created_at: datetime


# ─────────────────────────────────────────────────────────────
# Users / Auth
# ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    username: str
    avatar_url: Optional[str] = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
