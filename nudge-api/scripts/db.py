"""Database setup.

    python -m scripts.db reset    drop everything, create the tables from db/schema.sql
    python -m scripts.db seed     clear the tables and load the example data
    python -m scripts.db setup    reset + seed
    python -m scripts.db migrate  add columns introduced since a database was created (keeps data)

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
from app.repositories.pg_seed import TABLES, clear, insert_seed
from app.repositories.postgres import PostgresRepository
from app.repositories.seed import default_seed

SCHEMA = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

# Additive changes to tables that already exist. Each is safe to run more than once.
MIGRATIONS = [
    "alter table materials add column if not exists error text",
    "alter table materials add column if not exists progress integer not null default 0",
    "alter table materials add column if not exists stage text",
    "alter table materials add column if not exists processing_started_at timestamptz",
]


def migrate(database_url: str) -> None:
    with psycopg.connect(database_url, autocommit=True) as conn:
        for statement in MIGRATIONS:
            conn.execute(statement)
    print(f"Applied {len(MIGRATIONS)} migrations")


def reset(database_url: str) -> None:
    # Drop only Nudge's tables, so anything else in the database (like Supabase's
    # own settings on the public schema) is left alone.
    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute(f"drop table if exists {', '.join(TABLES)} cascade")
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
    if command == "migrate":
        migrate(url)
    if command in ("reset", "setup"):
        reset(url)
    if command in ("seed", "setup"):
        seed(url)
    if command not in ("reset", "seed", "setup", "migrate"):
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
