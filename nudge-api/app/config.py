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
    storage: Literal["mock", "gcs"] = "mock"
    auth: Literal["mock"] = "mock"

    # Postgres (Supabase). Read as NUDGE_DATABASE_URL.
    database_url: str | None = None
    # Gemini and Google Cloud Storage.
    gemini_api_key: str | None = None
    bucket: str = "nudge-course-files"

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
