from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPOSITORY_DIR = BACKEND_DIR.parent


def parse_origins(value: Any) -> list[str]:
    if isinstance(value, str):
        return [origin.strip() for origin in value.split(",") if origin.strip()]
    if isinstance(value, list):
        return [str(origin).rstrip("/") for origin in value]
    raise ValueError("CORS_ALLOWED_ORIGINS must be a comma-separated string or list")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(REPOSITORY_DIR / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )

    APP_NAME: str = "Lucidex API"
    ENV: Literal["development", "test", "production"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    MONGODB_URI: str
    MONGODB_DB_NAME: str = "lucidex"

    JWT_SECRET_KEY: str = Field(min_length=32)
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: str = "redis://localhost:6379/0"

    EMAIL_SMTP_HOST: str | None = None
    EMAIL_SMTP_PORT: int | None = None
    EMAIL_SMTP_USER: str | None = None
    EMAIL_SMTP_PASSWORD: str | None = None
    SMS_GATEWAY_API_KEY: str | None = None

    EKYC_PROVIDER: str = "fpt_ai"
    EKYC_MOCK_MODE: bool = True
    EKYC_MOCK_SCORE: int = 95
    FPT_AI_API_KEY: str | None = None
    FPT_AI_OCR_URL: str = "https://api.fpt.ai/vision/ocr"
    FPT_AI_LIVENESS_URL: str = "https://api.fpt.ai/dmp/liveness/v3"
    FPT_AI_FACEMATCH_URL: str = "https://api.fpt.ai/dmp/liveness/v3"

    EKYC_CAPTURE_SESSION_TTL_MINUTES: int = 10
    FRONTEND_MOBILE_CAPTURE_BASE_URL: str = (
        "http://localhost:5173/mobile-capture"
    )

    FILE_STORAGE_BACKEND: Literal["local", "s3"] = "local"
    FILE_STORAGE_PATH: str = "./uploads"
    S3_BUCKET_NAME: str | None = None
    S3_ACCESS_KEY: str | None = None
    S3_SECRET_KEY: str | None = None

    CORS_ALLOWED_ORIGINS: Annotated[
        list[str], NoDecode, BeforeValidator(parse_origins)
    ] = []


settings = Settings()  # type: ignore[call-arg]
