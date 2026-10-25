"""In-memory repository used while the backend is mocked.

Data lives in plain dicts and is reset to the seed (seed.py) on every restart.
Search is deliberately simple: "by meaning" returns the course's chunks in
order and "by keyword" matches words, which is enough to exercise the RAG flow.
"""

import copy
import re
import threading
from dataclasses import replace
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
from app.repositories.seed import SeedData, default_seed


class InMemoryRepository(Repository):
    def __init__(self, seed: SeedData | None = None):
        seed = copy.deepcopy(seed) if seed else default_seed()
        self._lock = threading.RLock()
        self.users = {u.id: u for u in seed.users}
        self.courses = {c.id: c for c in seed.courses}
        self.enrollments: list[tuple[str, str]] = list(seed.enrollments)
        self.materials = {m.id: m for m in seed.materials}
        self.assignments = {a.id: a for a in seed.assignments}
        self.chunks = {c.id: c for c in seed.chunks}
        self.threads = {t.id: t for t in seed.threads}
        self.messages = {m.id: m for m in seed.messages}
        self.flags = {f.id: f for f in seed.flags}
        self.trending = {t.id: t for t in seed.trending}

    # ---- users ----

    def get_user(self, user_id: str) -> User | None:
        return self.users.get(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        email = email.strip().lower()
        return next((u for u in self.users.values() if u.email.lower() == email), None)

    def update_user_notifications(self, user_id: str, changes: dict[str, bool]) -> dict[str, bool]:
        with self._lock:
            user = self.users[user_id]
            user.notifications = {**user.notifications, **changes}
            return dict(user.notifications)

    # ---- courses ----

    def get_course(self, course_id: str) -> Course | None:
        return self.courses.get(course_id)

    def get_course_by_join_code(self, join_code: str) -> Course | None:
        join_code = join_code.strip().upper()
        return next((c for c in self.courses.values() if c.join_code == join_code), None)

    def list_courses_for_student(self, user_id: str) -> list[Course]:
        return [self.courses[cid] for uid, cid in self.enrollments if uid == user_id]

    def list_courses_for_teacher(self, teacher_id: str) -> list[Course]:
        return [c for c in self.courses.values() if c.teacher_id == teacher_id]

    def create_course(self, course: Course) -> Course:
        with self._lock:
            self.courses[course.id] = course
            return course

    def update_course_settings(self, course_id: str, changes: dict[str, bool]) -> CourseSettings:
        with self._lock:
            course = self.courses[course_id]
            course.settings = replace(course.settings, **changes)
            return course.settings

    # ---- enrollments ----

    def is_enrolled(self, user_id: str, course_id: str) -> bool:
        return (user_id, course_id) in self.enrollments

    def enroll(self, user_id: str, course_id: str) -> None:
        with self._lock:
            if (user_id, course_id) not in self.enrollments:
                self.enrollments.append((user_id, course_id))

    def count_students(self, course_id: str) -> int:
        return sum(1 for _, cid in self.enrollments if cid == course_id)

    # ---- materials ----

    def get_material(self, material_id: str) -> Material | None:
        return self.materials.get(material_id)

    def list_materials(self, course_id: str, include_restricted: bool) -> list[Material]:
        return [
            m
            for m in self.materials.values()
            if m.course_id == course_id and (include_restricted or not m.restricted)
        ]

    def count_materials(self, course_id: str) -> int:
        return len(self.list_materials(course_id, include_restricted=True))

    def create_material(self, material: Material) -> Material:
        with self._lock:
            self.materials[material.id] = material
            return material

    def set_material_status(self, material_id: str, status: MaterialStatus) -> None:
        with self._lock:
            self.materials[material_id].status = status

    # ---- assignments ----

    def get_assignment(self, assignment_id: str) -> Assignment | None:
        return self.assignments.get(assignment_id)

    def list_assignments(self, course_id: str) -> list[Assignment]:
        items = [a for a in self.assignments.values() if a.course_id == course_id]
        return sorted(items, key=lambda a: (a.due_at is None, a.due_at or datetime.max))

    def create_assignment(self, assignment: Assignment) -> Assignment:
        with self._lock:
            self.assignments[assignment.id] = assignment
            return assignment

    # ---- chunks ----

    def list_chunks(self, material_id: str) -> list[Chunk]:
        return [c for c in self.chunks.values() if c.material_id == material_id]

    def add_chunks(self, chunks: list[Chunk]) -> None:
        with self._lock:
            for chunk in chunks:
                self.chunks[chunk.id] = chunk

    def _course_chunks(self, course_id: str, include_restricted: bool) -> list[Chunk]:
        return [
            c
            for c in self.chunks.values()
            if c.course_id == course_id and (include_restricted or not c.restricted)
        ]

    def search_chunks_by_embedding(
        self, course_id: str, embedding: list[float], limit: int, include_restricted: bool
    ) -> list[Chunk]:
        # Mock embeddings carry no meaning, so return chunks in insertion order.
        return self._course_chunks(course_id, include_restricted)[:limit]

    def search_chunks_by_keyword(
        self, course_id: str, query: str, limit: int, include_restricted: bool
    ) -> list[Chunk]:
        words = {w for w in re.findall(r"\w+", query.lower()) if len(w) > 2}
        if not words:
            return []
        scored = []
        for chunk in self._course_chunks(course_id, include_restricted):
            text = f"{chunk.heading or ''} {chunk.content}".lower()
            score = sum(text.count(w) for w in words)
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [chunk for _, chunk in scored[:limit]]

    # ---- threads and messages ----

    def get_thread(self, thread_id: str) -> Thread | None:
        return self.threads.get(thread_id)

    def list_threads(self, user_id: str, query: str | None) -> list[Thread]:
        items = [t for t in self.threads.values() if t.user_id == user_id]
        if query:
            items = [t for t in items if query.lower() in t.title.lower()]
        return sorted(items, key=lambda t: t.updated_at, reverse=True)

    def create_thread(self, thread: Thread) -> Thread:
        with self._lock:
            self.threads[thread.id] = thread
            return thread

    def touch_thread(self, thread_id: str, updated_at: datetime) -> None:
        with self._lock:
            self.threads[thread_id].updated_at = updated_at

    def get_message(self, message_id: str) -> Message | None:
        return self.messages.get(message_id)

    def list_messages(self, thread_id: str) -> list[Message]:
        items = [m for m in self.messages.values() if m.thread_id == thread_id]
        return sorted(items, key=lambda m: m.created_at)

    def add_message(self, message: Message) -> Message:
        with self._lock:
            self.messages[message.id] = message
            return message

    # ---- flags ----

    def add_flag(self, flag: Flag) -> Flag:
        with self._lock:
            self.flags[flag.id] = flag
            return flag

    def count_flags_for_message(self, message_id: str) -> int:
        return sum(1 for f in self.flags.values() if f.message_id == message_id)

    def list_open_flags(self, course_id: str) -> list[Flag]:
        first_per_message: dict[str, Flag] = {}
        for flag in sorted(self.flags.values(), key=lambda f: f.created_at):
            if flag.course_id == course_id and flag.status == "open":
                first_per_message.setdefault(flag.message_id, flag)
        return sorted(first_per_message.values(), key=lambda f: f.created_at, reverse=True)

    # ---- stats ----

    def _student_messages(self, user_id: str) -> list[Message]:
        thread_ids = {t.id for t in self.threads.values() if t.user_id == user_id}
        return [m for m in self.messages.values() if m.thread_id in thread_ids and m.role == "student"]

    def count_student_messages(self, user_id: str, with_photo: bool = False) -> int:
        return sum(1 for m in self._student_messages(user_id) if not with_photo or m.attachment_path)

    def count_assignment_threads(self, user_id: str) -> int:
        return len(
            {t.assignment_id for t in self.threads.values() if t.user_id == user_id and t.assignment_id}
        )

    def course_activity(self, course_id: str, since: datetime) -> tuple[int, int]:
        threads = {t.id: t for t in self.threads.values() if t.course_id == course_id}
        questions = [
            m
            for m in self.messages.values()
            if m.thread_id in threads and m.role == "student" and m.created_at >= since
        ]
        students = {threads[m.thread_id].user_id for m in questions}
        return len(questions), len(students)

    def list_trending_topics(self, course_id: str, limit: int) -> list[TrendingTopic]:
        items = [t for t in self.trending.values() if t.course_id == course_id]
        return sorted(items, key=lambda t: t.student_count, reverse=True)[:limit]
