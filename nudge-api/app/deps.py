"""Wiring. Picks an implementation for each dependency from Settings and hands
services to the routers through FastAPI's Depends.

To add a real implementation (Postgres, Gemini, GCS), write the class and add
a branch in the matching build_* function. Nothing else changes.
"""

from dataclasses import dataclass

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings
from app.domain import User
from app.errors import forbidden
from app.integrations.ai import AIClient, MockAIClient
from app.integrations.auth import AuthProvider, JWTAuthProvider, MockAuthProvider
from app.integrations.storage import LocalStorage, MockStorage, StorageClient
from app.repositories.base import Repository
from app.repositories.memory import InMemoryRepository
from app.services.auth import AuthService
from app.services.chat import ChatService
from app.services.ingestion import IngestionService
from app.services.student import StudentService
from app.services.teacher import TeacherService
from app.services.threads import ThreadService
from app.services.views import Views


def build_repository(settings: Settings) -> Repository:
    if settings.repository == "postgres":
        from app.repositories.postgres import PostgresRepository

        if not settings.database_url:
            raise RuntimeError("Set NUDGE_DATABASE_URL to use the Postgres repository.")
        return PostgresRepository(settings.database_url)
    return InMemoryRepository()


def build_ai(settings: Settings) -> AIClient:
    if settings.ai == "gemini":
        from app.integrations.gemini import GeminiClient

        if not settings.gemini_api_key:
            raise RuntimeError("Set NUDGE_GEMINI_API_KEY to use Gemini.")
        return GeminiClient(
            settings.gemini_api_key,
            chat_models=settings.gemini_chat_models,
            transcribe_models=settings.gemini_transcribe_models,
            embedding_model=settings.gemini_embedding_model,
            timeout_seconds=settings.gemini_timeout_seconds,
        )
    return MockAIClient()


def build_storage(settings: Settings) -> StorageClient:
    if settings.storage == "local":
        return LocalStorage(settings.local_storage_dir, settings.bucket)
    if settings.storage == "gcs":
        from app.integrations.storage import GCSStorage

        return GCSStorage(settings.bucket, settings.gcs_signer)
    return MockStorage(settings.bucket)


def build_auth(settings: Settings) -> AuthProvider:
    if settings.auth == "jwt":
        if not settings.jwt_secret:
            raise RuntimeError("Set NUDGE_JWT_SECRET to use real login.")
        return JWTAuthProvider(settings.jwt_secret, settings.token_days)
    return MockAuthProvider()


@dataclass
class Container:
    settings: Settings
    repo: Repository
    ai: AIClient
    storage: StorageClient
    auth_provider: AuthProvider

    @classmethod
    def build(cls, settings: Settings) -> "Container":
        return cls(
            settings=settings,
            repo=build_repository(settings),
            ai=build_ai(settings),
            storage=build_storage(settings),
            auth_provider=build_auth(settings),
        )

    @property
    def views(self) -> Views:
        return Views(self.repo, self.storage, self.settings)

    @property
    def auth(self) -> AuthService:
        return AuthService(self.repo, self.auth_provider)

    @property
    def student(self) -> StudentService:
        return StudentService(self.repo, self.storage, self.views, self.settings)

    @property
    def threads(self) -> ThreadService:
        return ThreadService(self.repo, self.storage, ChatService(self.repo, self.ai), self.views)

    @property
    def teacher(self) -> TeacherService:
        return TeacherService(self.repo, self.storage, self.views, self.settings)

    @property
    def ingestion(self) -> IngestionService:
        delay = self.settings.mock_processing_seconds if self.settings.ai == "mock" else 0.0
        return IngestionService(self.repo, self.ai, self.storage, mock_delay_seconds=delay)


# ---- FastAPI dependencies ----

def get_container(request: Request) -> Container:
    return request.app.state.container


def get_auth_service(container: Container = Depends(get_container)) -> AuthService:
    return container.auth


def get_student_service(container: Container = Depends(get_container)) -> StudentService:
    return container.student


def get_thread_service(container: Container = Depends(get_container)) -> ThreadService:
    return container.threads


def get_teacher_service(container: Container = Depends(get_container)) -> TeacherService:
    return container.teacher


def get_ingestion_service(container: Container = Depends(get_container)) -> IngestionService:
    return container.ingestion


_bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth: AuthService = Depends(get_auth_service),
) -> User:
    return auth.user_for_token(credentials.credentials if credentials else None)


def current_student(user: User = Depends(current_user)) -> User:
    if user.role != "student":
        raise forbidden("This is for students. Sign in with a student account.")
    return user


def current_teacher(user: User = Depends(current_user)) -> User:
    if user.role != "teacher":
        raise forbidden("This is for teachers. Sign in with a teacher account.")
    return user
