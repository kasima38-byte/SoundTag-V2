import uuid
from datetime import datetime
from sqlalchemy import (
    BigInteger, Boolean, Column, DateTime, Float, ForeignKey,
    Integer, SmallInteger, String, Text, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import relationship
from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email         = Column(String(255), unique=True, nullable=False, index=True)
    username      = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    avatar_url    = Column(Text)
    is_active     = Column(Boolean, default=True, nullable=False)
    is_verified   = Column(Boolean, default=False, nullable=False)
    created_at    = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at    = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    history   = relationship("RecognitionHistory", back_populates="user", lazy="dynamic")
    favorites = relationship("Favorite", back_populates="user", lazy="dynamic")


class Song(Base):
    __tablename__ = "songs"

    id                = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title             = Column(String(512), nullable=False)
    artist            = Column(String(512), nullable=False)
    album             = Column(String(512))
    release_year      = Column(SmallInteger)
    duration_ms       = Column(Integer)
    genre             = Column(String(128))
    isrc              = Column(String(12), unique=True)
    artwork_url       = Column(Text)
    spotify_url       = Column(Text)
    apple_music_url   = Column(Text)
    youtube_url       = Column(Text)
    fingerprint_count = Column(Integer, default=0, nullable=False)
    created_at        = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at        = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    fingerprints = relationship("AudioFingerprint", back_populates="song", lazy="dynamic")
    history      = relationship("RecognitionHistory", back_populates="song", lazy="dynamic")
    favorites    = relationship("Favorite", back_populates="song", lazy="dynamic")


class AudioFingerprint(Base):
    __tablename__ = "audio_fingerprints"

    id           = Column(BigInteger, primary_key=True, autoincrement=True)
    song_id      = Column(UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), nullable=False, index=True)
    address_hash = Column(BigInteger, nullable=False, index=True)
    time_offset  = Column(Integer, nullable=False)
    created_at   = Column(DateTime(timezone=True), default=datetime.utcnow)

    song = relationship("Song", back_populates="fingerprints")


class RecognitionHistory(Base):
    __tablename__ = "recognition_history"

    id               = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id          = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    song_id          = Column(UUID(as_uuid=True), ForeignKey("songs.id", ondelete="SET NULL"), nullable=True)
    confidence       = Column(Float)
    matched          = Column(Boolean, default=False, nullable=False)
    audio_duration_ms= Column(Integer)
    device_os        = Column(String(32))
    ip_address       = Column(INET)
    recognized_at    = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="history")
    song = relationship("Song", back_populates="history")


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "song_id"),)

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    song_id    = Column(UUID(as_uuid=True), ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="favorites")
    song = relationship("Song", back_populates="favorites")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked    = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
