"""Postgres (Supabase + pgvector) repository.

Turn it on with NUDGE_REPOSITORY=postgres and NUDGE_DATABASE_URL in .env, after
running db/schema.sql. The class must implement every method in
repositories/base.py. A few are written as examples. They have not been run
against a database yet. The rest raise NotImplementedError until someone fills
them in.

Tip: run the API tests with NUDGE_REPOSITORY=postgres against a seeded
database to check a new implementation behaves like the in-memory one.
"""

from datetime import datetime

from app.domain import (
    Assignment,
    Chunk,
    Course,
    CourseSettings,
    Flag,
    Material,
    MaterialStatus,
    Message,
    Thread,
    TrendingTopic,
    User,
)
from app.repositories.base import Repository


def _todo(name: str):
    raise NotImplementedError(f"PostgresRepository.{name} is not written yet")


class PostgresRepository(Repository):
    def __init__(self, database_url: str):
        # Imported here so the mock runs without the Postgres packages installed.
        from pgvector.psycopg import register_vector
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self.pool = ConnectionPool(
            database_url,
            kwargs={"row_factory": dict_row},
            configure=register_vector,
            open=True,
        )

    def _all(self, sql: str, params: dict | None = None) -> list[dict]:
        with self.pool.connection() as conn:
            return conn.execute(sql, params or {}).fetchall()

    def _one(self, sql: str, params: dict | None = None) -> dict | None:
        with self.pool.connection() as conn:
            return conn.execute(sql, params or {}).fetchone()

    def _execute(self, sql: str, params: dict | None = None) -> None:
        with self.pool.connection() as conn:
            conn.execute(sql, params or {})

    # ---- users ----

    def get_user(self, user_id: str) -> User | None:
        row = self._one(
            "select id::text, name, email, role, department, notifications, created_at "
            "from users where id = %(id)s",
            {"id": user_id},
        )
        return User(**row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        row = self._one(
            "select id::text, name, email, role, department, notifications, created_at "
            "from users where lower(email) = lower(%(email)s)",
            {"email": email.strip()},
        )
        return User(**row) if row else None

    def update_user_notifications(self, user_id: str, changes: dict[str, bool]) -> dict[str, bool]:
        _todo("update_user_notifications")  # update users set notifications = notifications || %s

    # ---- courses ----

    def get_course(self, course_id: str) -> Course | None:
        _todo("get_course")

    def get_course_by_join_code(self, join_code: str) -> Course | None:
        _todo("get_course_by_join_code")

    def list_courses_for_student(self, user_id: str) -> list[Course]:
        _todo("list_courses_for_student")

    def list_courses_for_teacher(self, teacher_id: str) -> list[Course]:
        _todo("list_courses_for_teacher")

    def create_course(self, course: Course) -> Course:
        _todo("create_course")

    def update_course_settings(self, course_id: str, changes: dict[str, bool]) -> CourseSettings:
        _todo("update_course_settings")

    # ---- enrollments ----

    def is_enrolled(self, user_id: str, course_id: str) -> bool:
        _todo("is_enrolled")

    def enroll(self, user_id: str, course_id: str) -> None:
        _todo("enroll")  # insert ... on conflict do nothing

    def count_students(self, course_id: str) -> int:
        _todo("count_students")

    # ---- materials ----

    def get_material(self, material_id: str) -> Material | None:
        _todo("get_material")

    def list_materials(self, course_id: str, include_restricted: bool) -> list[Material]:
        _todo("list_materials")

    def count_materials(self, course_id: str) -> int:
        _todo("count_materials")

    def create_material(self, material: Material) -> Material:
        _todo("create_material")

    def set_material_status(self, material_id: str, status: MaterialStatus) -> None:
        _todo("set_material_status")

    # ---- assignments ----

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        _todo("get_assignment")

    def list_assignments(self, course_id: str) -> list[Assignment]:
        _todo("list_assignments")  # order by due_at nulls last

    def create_assignment(self, assignment: Assignment) -> Assignment:
        _todo("create_assignment")

    # ---- chunks ----

    def list_chunks(self, material_id: str) -> list[Chunk]:
        _todo("list_chunks")

    def add_chunks(self, chunks: list[Chunk]) -> None:
        _todo("add_chunks")  # executemany insert into chunks

    def search_chunks_by_embedding(
        self, course_id: str, embedding: list[float], limit: int, include_restricted: bool
    ) -> list[Chunk]:
        import numpy as np

        rows = self._all(
            """
            select id::text, course_id::text, material_id::text, content, page, heading, restricted
            from chunks
            where course_id = %(course_id)s and (%(include_restricted)s or restricted = false)
            order by embedding <=> %(embedding)s
            limit %(limit)s
            """,
            {
                "course_id": course_id,
                "embedding": np.array(embedding),
                "include_restricted": include_restricted,
                "limit": limit,
            },
        )
        return [Chunk(**row) for row in rows]

    def search_chunks_by_keyword(
        self, course_id: str, query: str, limit: int, include_restricted: bool
    ) -> list[Chunk]:
        rows = self._all(
            """
            select id::text, course_id::text, material_id::text, content, page, heading, restricted
            from chunks
            where course_id = %(course_id)s and (%(include_restricted)s or restricted = false)
              and search @@ websearch_to_tsquery('english', %(query)s)
            order by ts_rank(search, websearch_to_tsquery('english', %(query)s)) desc
            limit %(limit)s
            """,
            {
                "course_id": course_id,
                "query": query,
                "include_restricted": include_restricted,
                "limit": limit,
            },
        )
        return [Chunk(**row) for row in rows]

    # ---- threads and messages ----

    def get_thread(self, thread_id: str) -> Thread | None:
        _todo("get_thread")

    def list_threads(self, user_id: str, query: str | None) -> list[Thread]:
        _todo("list_threads")  # title ilike '%' || query || '%'

    def create_thread(self, thread: Thread) -> Thread:
        _todo("create_thread")

    def touch_thread(self, thread_id: str, updated_at: datetime) -> None:
        _todo("touch_thread")

    def get_message(self, message_id: str) -> Message | None:
        _todo("get_message")

    def list_messages(self, thread_id: str) -> list[Message]:
        _todo("list_messages")

    def add_message(self, message: Message) -> Message:
        _todo("add_message")  # citations go in the jsonb column

    # ---- flags ----

    def add_flag(self, flag: Flag) -> Flag:
        _todo("add_flag")

    def count_flags_for_message(self, message_id: str) -> int:
        _todo("count_flags_for_message")

    def list_open_flags(self, course_id: str) -> list[Flag]:
        _todo("list_open_flags")  # distinct on (message_id) ... order by message_id, created_at

    # ---- stats ----

    def count_student_messages(self, user_id: str, with_photo: bool = False) -> int:
        _todo("count_student_messages")

    def count_assignment_threads(self, user_id: str) -> int:
        _todo("count_assignment_threads")

    def course_activity(self, course_id: str, since: datetime) -> tuple[int, int]:
        _todo("course_activity")

    def list_trending_topics(self, course_id: str, limit: int) -> list[TrendingTopic]:
        _todo("list_trending_topics")
