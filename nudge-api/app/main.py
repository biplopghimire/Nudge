"""Nudge API. Run with: uvicorn app.main:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.deps import Container
from app.errors import register_error_handlers
from app.routers import auth, student, teacher, threads


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="Nudge API",
        description="Backend for Nudge. Mock mode: " + ", ".join(
            f"{name}={getattr(settings, name)}" for name in ("repository", "ai", "storage", "auth")
        ),
    )
    app.state.container = Container.build(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(auth.router)
    app.include_router(threads.router)
    app.include_router(student.router)
    app.include_router(teacher.router)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok"}

    return app


app = create_app()
