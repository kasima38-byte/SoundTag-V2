from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "SoundTag"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 40

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_TTL_SECONDS: int = 300

    # Storage (S3 or GCS)
    STORAGE_BACKEND: str = "s3"  # "s3" | "gcs"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "soundtag-assets"

    # Audio fingerprinting
    SAMPLE_RATE: int = 22050
    AUDIO_DURATION_SEC: int = 10
    FFT_WINDOW_SIZE: int = 4096
    HOP_LENGTH: int = 512
    NUM_PEAKS: int = 15          # peaks per spectrogram frame
    FAN_VALUE: int = 10          # constellation pairs per peak
    MIN_HASH_TIME_DELTA: int = 0
    MAX_HASH_TIME_DELTA: int = 200
    FINGERPRINT_REDUCTION: int = 20

    # Recognition thresholds
    MIN_FINGERPRINT_MATCHES: int = 5
    CONFIDENCE_THRESHOLD: float = 0.3

    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
