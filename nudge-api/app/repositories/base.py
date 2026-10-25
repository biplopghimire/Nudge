"""The data-access contract.

Every read and write the services make goes through one of these methods, so
switching from the in-memory mock to Postgres means writing one class
(PostgresRepository) that implements them. Nothing in services/ or routers/
has to change.

Rules for implementations:
- Return domain records (app/domain.py) or None when a row is not found.
- Do not check permissions here. Services decide who may see what.
- Writes return the stored record so services can respond with it.
"""

from abc import ABC, abstractmethod
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


class Repository(ABC):
    # ---- users ----

    @abstractmethod
    def get_user(self, user_id: str) -> User | None: ...

    @abstractmethod
    def get_user_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def update_user_notifications(self, user_id: str, changes: dict[str, bool]) -> dict[str, bool]:
        """Merge `changes` into users.notifications and return the full result."""

    # ---- courses ----

    @abstractmethod
    def get_course(self, course_id: str) -> Course | None: ...

    @abstractmethod
    def get_course_by_join_code(self, join_code: str) -> Course | None: ...

    @abstractmethod
    def list_courses_for_student(self, user_id: str) -> list[Course]:
        """Courses the student is enrolled in, oldest enrollment first."""

    @abstractmethod
    def list_courses_for_teacher(self, teacher_id: str) -> list[Course]: ...

    @abstractmethod
    def create_course(self, course: Course) -> Course: ...

    @abstractmethod
    def update_course_settings(self, course_id: str, changes: dict[str, bool]) -> CourseSettings:
        """`changes` uses CourseSettings field names (snake_case)."""

    # ---- enrollments ----

    @abstractmethod
    def is_enrolled(self, user_id: str, course_id: str) -> bool: ...

    @abstractmethod
    def enroll(self, user_id: str, course_id: str) -> None:
        """Does nothing if the student is already enrolled."""

    @abstractmethod
    def count_students(self, course_id: str) -> int: ...

    # ---- materials ----

    @abstractmethod
    def get_material(self, material_id: str) -> Material | None: ...

    @abstractmethod
    def list_materials(self, course_id: str, include_restricted: bool) -> list[Material]: ...

    @abstractmethod
    def count_materials(self, course_id: str) -> int: ...

    @abstractmethod
    def create_material(self, material: Material) -> Material: ...

    @abstractmethod
    def set_material_status(self, material_id: str, status: MaterialStatus) -> None: ...

    # ---- assignments ----

    @abstractmethod
    def get_assignment(self, assignment_id: str) -> Assignment | None: ...

    @abstractmethod
    def list_assignments(self, course_id: str) -> list[Assignment]:
        """Ordered by due date, assignments without one last."""

    @abstractmethod
    def create_assignment(self, assignment: Assignment) -> Assignment: ...

    # ---- chunks (RAG) ----

    @abstractmethod
    def list_chunks(self, material_id: str) -> list[Chunk]: ...

    @abstractmethod
    def add_chunks(self, chunks: list[Chunk]) -> None: ...

    @abstractmethod
    def search_chunks_by_embedding(
        self, course_id: str, embedding: list[float], limit: int, include_restricted: bool
    ) -> list[Chunk]:
        """Nearest chunks by cosine distance (Part 4, 'by meaning')."""

    @abstractmethod
    def search_chunks_by_keyword(
        self, course_id: str, query: str, limit: int, include_restricted: bool
    ) -> list[Chunk]:
        """Full-text search ranked by ts_rank (Part 4, 'by keyword')."""

    # ---- threads and messages ----

    @abstractmethod
    def get_thread(self, thread_id: str) -> Thread | None: ...

    @abstractmethod
    def list_threads(self, user_id: str, query: str | None) -> list[Thread]:
        """Newest first. `query` filters by title, case-insensitive."""

    @abstractmethod
    def create_thread(self, thread: Thread) -> Thread: ...

    @abstractmethod
    def touch_thread(self, thread_id: str, updated_at: datetime) -> None: ...

    @abstractmethod
    def get_message(self, message_id: str) -> Message | None: ...

    @abstractmethod
    def list_messages(self, thread_id: str) -> list[Message]:
        """Oldest first."""

    @abstractmethod
    def add_message(self, message: Message) -> Message: ...

    # ---- flags ----

    @abstractmethod
    def add_flag(self, flag: Flag) -> Flag: ...

    @abstractmethod
    def count_flags_for_message(self, message_id: str) -> int: ...

    @abstractmethod
    def list_open_flags(self, course_id: str) -> list[Flag]:
        """One flag per message (the earliest), newest first."""

    # ---- stats ----

    @abstractmethod
    def count_student_messages(self, user_id: str, with_photo: bool = False) -> int:
        """Messages the student sent, across all their chats."""

    @abstractmethod
    def count_assignment_threads(self, user_id: str) -> int:
        """Distinct assignments the student has chatted about."""

    @abstractmethod
    def course_activity(self, course_id: str, since: datetime) -> tuple[int, int]:
        """(student questions, distinct students asking) since a time."""

    @abstractmethod
    def list_trending_topics(self, course_id: str, limit: int) -> list[TrendingTopic]: ...
