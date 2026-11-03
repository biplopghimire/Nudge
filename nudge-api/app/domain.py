"""Internal records. Each class mirrors one row of a table in db/schema.sql.

Repositories return these, services turn them into API responses (app/schemas).
Field names are snake_case to match the database columns.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Role = Literal["student", "teacher"]
MaterialKind = Literal["slides", "notes", "homework", "syllabus", "photo", "other"]
MaterialStatus = Literal["processing", "ready", "failed"]
MessageRole = Literal["student", "teacher", "nudge"]
AttachmentType = Literal["image", "pdf"]
AttachmentSource = Literal["camera", "library", "files"]
FlagStatus = Literal["open", "resolved"]


@dataclass
class User:
    id: str
    name: str
    email: str
    role: Role
    department: str | None = None
    notifications: dict[str, bool] = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass
class CourseSettings:
    hints_only: bool = True
    use_solution_keys: bool = False
    cite_materials: bool = True
    deadline_reminders: bool = True  # on for every student; each can still mute it


@dataclass
class Course:
    id: str
    code: str
    section: str
    semester: str
    teacher_id: str
    join_code: str
    settings: CourseSettings = field(default_factory=CourseSettings)
    office_hours: str | None = None


@dataclass
class Material:
    id: str
    course_id: str
    title: str
    kind: MaterialKind
    size_bytes: int
    storage_path: str
    restricted: bool = False
    status: MaterialStatus = "processing"
    uploaded_at: datetime | None = None
    error: str | None = None  # why processing failed, in words a teacher can act on
    progress: int = 0  # 0-100 while processing
    stage: str | None = None  # "Reading pages 9-16 of 40"
    processing_started_at: datetime | None = None


@dataclass
class Assignment:
    id: str
    course_id: str
    title: str
    short_title: str | None = None
    material_id: str | None = None
    due_at: datetime | None = None


@dataclass
class Chunk:
    id: str
    course_id: str
    material_id: str
    content: str
    page: int | None = None
    heading: str | None = None
    restricted: bool = False
    embedding: list[float] | None = None


@dataclass
class Thread:
    id: str
    user_id: str
    course_id: str
    title: str
    updated_at: datetime
    assignment_id: str | None = None
    owner_role: Role = "student"


@dataclass
class Citation:
    material_id: str
    title: str
    page: int | None = None


@dataclass
class Message:
    id: str
    thread_id: str
    role: MessageRole
    content: str
    created_at: datetime
    attachment_path: str | None = None  # one-off context, never added to course materials
    attachment_type: AttachmentType | None = None
    attachment_source: AttachmentSource | None = None
    citations: list[Citation] = field(default_factory=list)


@dataclass
class Flag:
    id: str
    message_id: str
    course_id: str
    reason: str
    created_at: datetime
    note: str | None = None
    status: FlagStatus = "open"
    correction: str | None = None


@dataclass
class TrendingTopic:
    id: str
    course_id: str
    title: str
    student_count: int
