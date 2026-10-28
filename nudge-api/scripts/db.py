"""Database setup.

    python -m scripts.db reset    drop everything, create the tables from db/schema.sql
    python -m scripts.db seed     clear the tables and load the example data
    python -m scripts.db setup    reset + seed

Uses NUDGE_DATABASE_URL from .env. Seed embeddings come from the AI set by
NUDGE_AI (gemini gives real search results, mock gives placeholder vectors).
With NUDGE_AUTH=jwt, the example accounts get NUDGE_SEED_PASSWORD as their password.
"""

import copy
import sys
from pathlib import Path

import psycopg

from app.config import get_settings
from app.deps import build_ai, build_auth
from app.repositories.pg_seed import clear, insert_seed
from app.repositories.postgres import PostgresRepository
from app.repositories.seed import default_seed

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"


def reset(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("drop schema if exists public cascade")
        conn.execute("create schema public")
        conn.execute(SCHEMA.read_text())
    print(f"Created tables from {SCHEMA.name}")


def seed(database_url: str) -> None:
    settings = get_settings()
    ai = build_ai(settings)
    password_hash = None
    if settings.auth == "jwt":
        if not settings.seed_password or len(settings.seed_password) < 8:
            sys.exit("Set NUDGE_SEED_PASSWORD (8+ characters) for the example accounts.")
        password_hash = build_auth(settings).hash_password(settings.seed_password)
    repo = PostgresRepository(database_url, max_size=2)
    try:
        clear(repo)
        insert_seed(
            repo, copy.deepcopy(default_seed()), lambda texts: ai.embed(texts, task="document"), password_hash
        )
    finally:
        repo.close()
    print(f"Loaded example data (embeddings: {settings.ai})")


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "setup"
    url = get_settings().database_url
    if not url:
        sys.exit("Set NUDGE_DATABASE_URL in .env first.")
    if command in ("reset", "setup"):
        reset(url)
    if command in ("seed", "setup"):
        seed(url)
    if command not in ("reset", "seed", "setup"):
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
