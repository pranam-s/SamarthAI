import secrets
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Samarth AI Resume Platform"
    ENVIRONMENT: str = "development"
    APP_URL: str = "http://localhost:8000"

    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 5
    AUTH_COOKIE_NAME: str = "access_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    CORS_ORIGINS: list[str] = ["http://localhost:8000", "http://127.0.0.1:8000"]

    DATABASE_URL: str = "sqlite+aiosqlite:///./job_matcher.db"

    AI_PRIMARY_PROVIDER: str = "google"
    AI_FALLBACK_PROVIDER: str = "openrouter"
    GOOGLE_API_KEY: str | None = None
    GEMINI_API_KEY: str | None = None
    GOOGLE_MODEL: str = "gemini-2.5-flash"
    GOOGLE_THINKING_BUDGET: int = 8192
    OPENROUTER_API_KEY: str | None = None
    OPENROUTER_MODEL: str = "google/gemini-2.5-flash"

    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024

    PROMPTS_DIR: str = str(BASE_DIR / "prompts")

    DEFAULT_LOCALE: str = "en"
    SUPPORTED_LOCALES: list[str] = [
        "en",
        "hi",
        "bn",
        "te",
        "mr",
        "ta",
        "ur",
        "gu",
        "kn",
        "ml",
        "es",
        "fr",
        "ar",
        "zh",
        "pt",
        "de",
        "ru",
        "ja",
        "ko",
        "it",
    ]

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @property
    def resolved_google_api_key(self) -> str | None:
        return self.GOOGLE_API_KEY or self.GEMINI_API_KEY


settings = Settings()
