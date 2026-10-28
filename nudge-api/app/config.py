"""Settings, read from environment variables or nudge-api/.env (see .env.example).

Each outside dependency has a switch. "mock" is the default for all of them,
so the API runs with no accounts or keys.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="NUDGE_", extra="ignore")

    # Which implementation to use for each dependency.
    repository: Literal["memory", "postgres"] = "memory"
    ai: Literal["mock", "gemini"] = "mock"
    storage: Literal["mock", "local", "gcs"] = "mock"
    auth: Literal["mock", "jwt"] = "mock"

    # Postgres (Supabase). Read as NUDGE_DATABASE_URL.
    database_url: str | None = None
    # Login tokens (NUDGE_AUTH=jwt). Make one with: python -c "import secrets; print(secrets.token_urlsafe(48))"
    jwt_secret: str | None = None
    token_days: int = 30
    # Password for the example accounts loaded by scripts/db.py when NUDGE_AUTH=jwt.
    seed_password: str | None = None

    # Gemini. Chat models are tried in order when one is overloaded.
    gemini_api_key: str | None = None
    gemini_chat_models: list[str] = ["gemini-3.5-flash", "gemini-2.5-flash", "gemini-3.5-flash-lite"]
    gemini_transcribe_models: list[str] = ["gemini-3.5-flash-lite", "gemini-2.5-flash"]
    gemini_embedding_model: str = "gemini-embedding-2"
    gemini_timeout_seconds: float = 45.0

    # File storage. "local" keeps files in local_storage_dir.
    bucket: str = "nudge-course-files"
    local_storage_dir: str = ".storage"

    # App behavior.
    current_semester: str = "Fall 2026"
    timezone: str = "America/New_York"
    signed_url_minutes: int = 15
    cors_origins: list[str] = ["*"]

    # Mock only: how long an upload stays "processing".
    mock_processing_seconds: float = 5.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
