"""Load SeedData (the same example data the in-memory repository uses) into Postgres."""

from collections.abc import Callable

from app.repositories.postgres import PostgresRepository
from app.repositories.seed import SeedData

TABLES = (
    "flags", "messages", "threads", "chunks", "assignments", "materials",
    "enrollments", "trending_topics", "courses", "users",
)


def clear(repo: PostgresRepository) -> None:
    repo._execute(f"truncate {', '.join(TABLES)} cascade")


def insert_seed(
    repo: PostgresRepository,
    seed: SeedData,
    embed: Callable[[list[str]], list[list[float]]],
    password_hash: str | None = None,
) -> None:
    """`embed` turns chunk text into vectors (the mock or Gemini). Every example
    account gets `password_hash` (None works only with mock login)."""
    for user in seed.users:
        repo.create_user(user, password_hash)
    for course in seed.courses:
        repo.create_course(course)
    for user_id, course_id in seed.enrollments:
        repo.enroll(user_id, course_id)
    for material in seed.materials:
        repo.create_material(material)
    for assignment in seed.assignments:
        repo.create_assignment(assignment)

    missing = [c for c in seed.chunks if c.embedding is None]
    for chunk, vector in zip(missing, embed([c.content for c in missing]) if missing else []):
        chunk.embedding = vector
    repo.add_chunks(seed.chunks)

    for thread in seed.threads:
        repo.create_thread(thread)
    for message in seed.messages:
        repo.add_message(message)
    for flag in seed.flags:
        repo.add_flag(flag)
    for topic in seed.trending:
        repo._execute(
            "insert into trending_topics (id, course_id, title, student_count) "
            "values (%(id)s, %(course_id)s, %(title)s, %(student_count)s)",
            topic.__dict__,
        )
