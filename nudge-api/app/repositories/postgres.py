"""Postgres + pgvector repository (local Postgres.app now, Supabase when deployed).

Turn it on with NUDGE_REPOSITORY=postgres and NUDGE_DATABASE_URL in .env, after
creating the tables (python -m scripts.db reset). Every method matches the
contract in repositories/base.py, and the API tests run against both this and
the in-memory repository.
"""

import json
from datetime import datetime

import numpy as np
from pgvector.psycopg import register_vector
from psycopg import Connection
from psycopg.rows import dict_row
from psycopg.types.string import TextLoader
from psycopg_pool import ConnectionPool

from app.domain import (
    Assignment,
    Chunk,
    Citation,
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

SETTINGS_COLUMNS = ("hints_only", "use_solution_keys", "cite_materials", "deadline_reminders")

COURSE_COLUMNS = (
    "id, code, section, semester, teacher_id, join_code, office_hours, " + ", ".join(SETTINGS_COLUMNS)
)
MATERIAL_COLUMNS = "id, course_id, title, kind, size_bytes, storage_path, restricted, status, uploaded_at"
CHUNK_COLUMNS = "id, course_id, material_id, content, page, heading, restricted"
THREAD_COLUMNS = "id, user_id, course_id, title, updated_at, assignment_id, owner_role"
MESSAGE_COLUMNS = (
    "id, thread_id, role, content, created_at, attachment_path, attachment_type, attachment_source, citations"
)
FLAG_COLUMNS = "id, message_id, course_id, reason, created_at, note, status, correction"


def configure_connection(conn: Connection) -> None:
    """pgvector types, and uuids as plain strings like the rest of the app uses."""
    register_vector(conn)
    conn.adapters.register_loader("uuid", TextLoader)


# ---- row -> domain ----

def _course(row: dict) -> Course:
    settings = CourseSettings(**{name: row.pop(name) for name in SETTINGS_COLUMNS})
    return Course(**row, settings=settings)


def _chunk(row: dict) -> Chunk:
    return Chunk(**row)


def _message(row: dict) -> Message:
    citations = [
        Citation(material_id=c["materialId"], title=c["title"], page=c.get("page")) for c in row.pop("citations")
    ]
    return Message(**row, citations=citations)


class PostgresRepository(Repository):
    def __init__(self, database_url: str, min_size: int = 1, max_size: int = 10):
        self.pool = ConnectionPool(
            database_url,
            min_size=min_size,
            max_size=max_size,
            kwargs={"row_factory": dict_row, "autocommit": True},
            configure=configure_connection,
            open=True,
        )

    def close(self) -> None:
        self.pool.close()

    def _all(self, sql: str, params: dict | None = None) -> list[dict]:
        with self.pool.connection() as conn:
            return conn.execute(sql, params or {}).fetchall()

    def _one(self, sql: str, params: dict | None = None) -> dict | None:
        with self.pool.connection() as conn:
            return conn.execute(sql, params or {}).fetchone()

    def _value(self, sql: str, params: dict | None = None):
        row = self._one(sql, params)
        return next(iter(row.values())) if row else None

    def _execute(self, sql: str, params: dict | None = None) -> None:
        with self.pool.connection() as conn:
            conn.execute(sql, params or {})

    # ---- users ----

    def get_user(self, user_id: str) -> User | None:
        row = self._one(
            "select id, name, email, role, department, notifications, created_at from users where id = %(id)s",
            {"id": user_id},
        )
        return User(**row) if row else None

    def get_user_by_email(self, email: str) -> User | None:
        row = self._one(
            "select id, name, email, role, department, notifications, created_at "
            "from users where lower(email) = lower(%(email)s)",
            {"email": email.strip()},
        )
        return User(**row) if row else None

    def create_user(self, user: User, password_hash: str | None) -> User:
        row = self._one(
            "insert into users (id, name, email, role, department, notifications, password_hash) "
            "values (%(id)s, %(name)s, %(email)s, %(role)s, %(department)s, %(notifications)s::jsonb, %(hash)s) "
            "returning id, name, email, role, department, notifications, created_at",
            {**user.__dict__, "notifications": json.dumps(user.notifications), "hash": password_hash},
        )
        return User(**row)

    def get_password_hash(self, user_id: str) -> str | None:
        return self._value("select password_hash from users where id = %(id)s", {"id": user_id})

    def update_user_notifications(self, user_id: str, changes: dict[str, bool]) -> dict[str, bool]:
        return self._value(
            "update users set notifications = notifications || %(changes)s::jsonb "
            "where id = %(id)s returning notifications",
            {"id": user_id, "changes": json.dumps(changes)},
        )

    # ---- courses ----

    def get_course(self, course_id: str) -> Course | None:
        row = self._one(f"select {COURSE_COLUMNS} from courses where id = %(id)s", {"id": course_id})
        return _course(row) if row else None

    def get_course_by_join_code(self, join_code: str) -> Course | None:
        row = self._one(
            f"select {COURSE_COLUMNS} from courses where join_code = upper(%(code)s)",
            {"code": join_code.strip()},
        )
        return _course(row) if row else None

    def list_courses_for_student(self, user_id: str) -> list[Course]:
        rows = self._all(
            f"select {', '.join('c.' + c.strip() for c in COURSE_COLUMNS.split(','))} "
            "from enrollments e join courses c on c.id = e.course_id "
            "where e.user_id = %(id)s order by e.joined_at, c.code",
            {"id": user_id},
        )
        return [_course(r) for r in rows]

    def list_courses_for_teacher(self, teacher_id: str) -> list[Course]:
        rows = self._all(
            f"select {COURSE_COLUMNS} from courses where teacher_id = %(id)s order by code, section",
            {"id": teacher_id},
        )
        return [_course(r) for r in rows]

    def create_course(self, course: Course) -> Course:
        params = {
            "id": course.id,
            "code": course.code,
            "section": course.section,
            "semester": course.semester,
            "teacher_id": course.teacher_id,
            "join_code": course.join_code,
            "office_hours": course.office_hours,
            **{name: getattr(course.settings, name) for name in SETTINGS_COLUMNS},
        }
        self._execute(
            f"insert into courses ({', '.join(params)}) values ({', '.join(f'%({k})s' for k in params)})",
            params,
        )
        return course

    def update_course_settings(self, course_id: str, changes: dict[str, bool]) -> CourseSettings:
        changes = {k: v for k, v in changes.items() if k in SETTINGS_COLUMNS}
        assignments = ", ".join(f"{k} = %({k})s" for k in changes) or "id = id"
        row = self._one(
            f"update courses set {assignments} where id = %(id)s returning {', '.join(SETTINGS_COLUMNS)}",
            {**changes, "id": course_id},
        )
        return CourseSettings(**row)

    # ---- enrollments ----

    def is_enrolled(self, user_id: str, course_id: str) -> bool:
        return bool(
            self._one(
                "select 1 from enrollments where user_id = %(u)s and course_id = %(c)s",
                {"u": user_id, "c": course_id},
            )
        )

    def enroll(self, user_id: str, course_id: str) -> None:
        self._execute(
            "insert into enrollments (user_id, course_id) values (%(u)s, %(c)s) on conflict do nothing",
            {"u": user_id, "c": course_id},
        )

    def count_students(self, course_id: str) -> int:
        return self._value("select count(*) from enrollments where course_id = %(c)s", {"c": course_id})

    # ---- materials ----

    def get_material(self, material_id: str) -> Material | None:
        row = self._one(f"select {MATERIAL_COLUMNS} from materials where id = %(id)s", {"id": material_id})
        return Material(**row) if row else None

    def list_materials(self, course_id: str, include_restricted: bool) -> list[Material]:
        rows = self._all(
            f"select {MATERIAL_COLUMNS} from materials "
            "where course_id = %(c)s and (%(r)s or not restricted) order by uploaded_at, title",
            {"c": course_id, "r": include_restricted},
        )
        return [Material(**r) for r in rows]

    def count_materials(self, course_id: str) -> int:
        return self._value("select count(*) from materials where course_id = %(c)s", {"c": course_id})

    def create_material(self, material: Material) -> Material:
        row = self._one(
            "insert into materials (id, course_id, title, kind, size_bytes, storage_path, restricted, status, "
            "uploaded_at) values (%(id)s, %(course_id)s, %(title)s, %(kind)s, %(size_bytes)s, %(storage_path)s, "
            "%(restricted)s, %(status)s, coalesce(%(uploaded_at)s, now())) "
            f"returning {MATERIAL_COLUMNS}",
            material.__dict__,
        )
        return Material(**row)

    def set_material_status(self, material_id: str, status: MaterialStatus) -> None:
        self._execute("update materials set status = %(s)s where id = %(id)s", {"s": status, "id": material_id})

    # ---- assignments ----

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        row = self._one(
            "select id, course_id, title, short_title, material_id, due_at from assignments where id = %(id)s",
            {"id": assignment_id},
        )
        return Assignment(**row) if row else None

    def list_assignments(self, course_id: str) -> list[Assignment]:
        rows = self._all(
            "select id, course_id, title, short_title, material_id, due_at from assignments "
            "where course_id = %(c)s order by due_at nulls last, title",
            {"c": course_id},
        )
        return [Assignment(**r) for r in rows]

    def create_assignment(self, assignment: Assignment) -> Assignment:
        self._execute(
            "insert into assignments (id, course_id, title, short_title, material_id, due_at) "
            "values (%(id)s, %(course_id)s, %(title)s, %(short_title)s, %(material_id)s, %(due_at)s)",
            assignment.__dict__,
        )
        return assignment

    # ---- chunks ----

    def list_chunks(self, material_id: str) -> list[Chunk]:
        rows = self._all(
            f"select {CHUNK_COLUMNS}, embedding from chunks where material_id = %(m)s order by page nulls first, id",
            {"m": material_id},
        )
        for row in rows:
            row["embedding"] = row["embedding"].to_list() if row["embedding"] is not None else None
        return [_chunk(r) for r in rows]

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        with self.pool.connection() as conn, conn.cursor() as cur:
            cur.executemany(
                "insert into chunks (id, course_id, material_id, page, heading, content, restricted, embedding) "
                "values (%(id)s, %(course_id)s, %(material_id)s, %(page)s, %(heading)s, %(content)s, "
                "%(restricted)s, %(embedding)s)",
                [{**c.__dict__, "embedding": np.array(c.embedding, dtype=np.float32)} for c in chunks],
            )

    def search_chunks_by_embedding(
        self, course_id: str, embedding: list[float], limit: int, include_restricted: bool
    ) -> list[Chunk]:
        rows = self._all(
            f"select {CHUNK_COLUMNS} from chunks "
            "where course_id = %(c)s and (%(r)s or not restricted) "
            "order by embedding <=> %(e)s limit %(limit)s",
            {
                "c": course_id,
                "r": include_restricted,
                "e": np.array(embedding, dtype=np.float32),
                "limit": limit,
            },
        )
        return [_chunk(r) for r in rows]

    def search_chunks_by_keyword(
        self, course_id: str, query: str, limit: int, include_restricted: bool
    ) -> list[Chunk]:
        # websearch_to_tsquery ANDs the words, which misses most chat questions.
        # OR them instead so any shared word counts, then rank by how well they match.
        rows = self._all(
            f"""
            with q as (
              select to_tsquery('simple', string_agg(quote_literal(lexeme), ' | ')) as query
              from unnest(to_tsvector('english', %(q)s)) as t(lexeme)
            )
            select {', '.join('c.' + c.strip() for c in CHUNK_COLUMNS.split(','))}
            from chunks c, q
            where q.query is not null
              and c.course_id = %(c)s and (%(r)s or not c.restricted)
              and c.search @@ q.query
            order by ts_rank(c.search, q.query) desc
            limit %(limit)s
            """,
            {"q": query, "c": course_id, "r": include_restricted, "limit": limit},
        )
        return [_chunk(r) for r in rows]

    # ---- threads and messages ----

    def get_thread(self, thread_id: str) -> Thread | None:
        row = self._one(f"select {THREAD_COLUMNS} from threads where id = %(id)s", {"id": thread_id})
        return Thread(**row) if row else None

    def list_threads(self, user_id: str, query: str | None) -> list[Thread]:
        rows = self._all(
            f"select {THREAD_COLUMNS} from threads where user_id = %(u)s "
            "and (%(q)s::text is null or title ilike '%%' || %(q)s || '%%') order by updated_at desc",
            {"u": user_id, "q": query or None},
        )
        return [Thread(**r) for r in rows]

    def create_thread(self, thread: Thread) -> Thread:
        self._execute(
            "insert into threads (id, user_id, course_id, title, updated_at, assignment_id, owner_role) "
            "values (%(id)s, %(user_id)s, %(course_id)s, %(title)s, %(updated_at)s, %(assignment_id)s, "
            "%(owner_role)s)",
            thread.__dict__,
        )
        return thread

    def touch_thread(self, thread_id: str, updated_at: datetime) -> None:
        self._execute("update threads set updated_at = %(t)s where id = %(id)s", {"t": updated_at, "id": thread_id})

    def get_message(self, message_id: str) -> Message | None:
        row = self._one(f"select {MESSAGE_COLUMNS} from messages where id = %(id)s", {"id": message_id})
        return _message(row) if row else None

    def list_messages(self, thread_id: str) -> list[Message]:
        rows = self._all(
            f"select {MESSAGE_COLUMNS} from messages where thread_id = %(t)s order by created_at, seq",
            {"t": thread_id},
        )
        return [_message(r) for r in rows]

    def add_message(self, message: Message) -> Message:
        citations = [{"materialId": c.material_id, "title": c.title, "page": c.page} for c in message.citations]
        self._execute(
            "insert into messages (id, thread_id, role, content, created_at, attachment_path, attachment_type, "
            "attachment_source, citations) values (%(id)s, %(thread_id)s, %(role)s, %(content)s, %(created_at)s, "
            "%(attachment_path)s, %(attachment_type)s, %(attachment_source)s, %(citations)s::jsonb)",
            {**message.__dict__, "citations": json.dumps(citations)},
        )
        return message

    # ---- flags ----

    def add_flag(self, flag: Flag) -> Flag:
        self._execute(
            "insert into flags (id, message_id, course_id, reason, created_at, note, status, correction) "
            "values (%(id)s, %(message_id)s, %(course_id)s, %(reason)s, %(created_at)s, %(note)s, %(status)s, "
            "%(correction)s)",
            flag.__dict__,
        )
        return flag

    def count_flags_for_message(self, message_id: str) -> int:
        return self._value("select count(*) from flags where message_id = %(m)s", {"m": message_id})

    def list_open_flags(self, course_id: str) -> list[Flag]:
        rows = self._all(
            f"""
            select * from (
              select distinct on (message_id) {FLAG_COLUMNS} from flags
              where course_id = %(c)s and status = 'open'
              order by message_id, created_at
            ) first_flags order by created_at desc
            """,
            {"c": course_id},
        )
        return [Flag(**r) for r in rows]

    # ---- stats ----

    def count_student_messages(self, user_id: str, with_photo: bool = False) -> int:
        return self._value(
            "select count(*) from messages m join threads t on t.id = m.thread_id "
            "where t.user_id = %(u)s and m.role = 'student' "
            "and (not %(photo)s or m.attachment_type = 'image')",
            {"u": user_id, "photo": with_photo},
        )

    def count_assignment_threads(self, user_id: str) -> int:
        return self._value(
            "select count(distinct assignment_id) from threads where user_id = %(u)s and assignment_id is not null",
            {"u": user_id},
        )

    def course_activity(self, course_id: str, since: datetime) -> tuple[int, int]:
        row = self._one(
            "select count(*) as questions, count(distinct t.user_id) as students "
            "from messages m join threads t on t.id = m.thread_id "
            "where t.course_id = %(c)s and t.owner_role = 'student' and m.role = 'student' "
            "and m.created_at >= %(since)s",
            {"c": course_id, "since": since},
        )
        return row["questions"], row["students"]

    def list_trending_topics(self, course_id: str, limit: int) -> list[TrendingTopic]:
        rows = self._all(
            "select id, course_id, title, student_count from trending_topics "
            "where course_id = %(c)s order by student_count desc limit %(limit)s",
            {"c": course_id, "limit": limit},
        )
        return [TrendingTopic(**r) for r in rows]
