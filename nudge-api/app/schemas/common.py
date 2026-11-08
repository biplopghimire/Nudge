"""Response and request shapes shared by students and teachers.

Python fields are snake_case. JSON is camelCase, matching the TypeScript types
in nudge-types.ts and the example JSON files.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class UserOut(CamelModel):
    id: str
    name: str
    email: str
    role: Literal["student", "teacher"]


class CourseOut(CamelModel):
    id: str
    code: str
    section: str
    semester: str
    teacher_name: str
    material_count: int
    student_count: int


class TeacherCourseOut(CourseOut):
    join_code: str


class CourseSummaryOut(CamelModel):
    id: str
    code: str
    section: str
    teacher_name: str
    next_due: str | None = None
    current_assignment_title: str | None = None


class AssignmentOut(CamelModel):
    id: str
    course_id: str
    course_code: str
    title: str
    short_title: str
    due_at: datetime | None = None


class MaterialOut(CamelModel):
    id: str
    course_id: str
    title: str
    kind: Literal["slides", "notes", "homework", "syllabus", "photo", "other"]
    size_bytes: int
    restricted: bool
    status: Literal["processing", "ready", "failed"]
    progress: int = 0  # 0-100 while processing
    stage: str | None = None  # "Reading page 16 of 40"
    eta_seconds: int | None = None  # rough time left while processing
    error: str | None = None  # why it failed, when status is "failed"


class ChatThreadOut(CamelModel):
    id: str
    course_id: str
    course_code: str
    assignment_id: str | None = None
    owner_role: Literal["student", "teacher"]
    title: str
    updated_at: datetime


class CitationOut(CamelModel):
    material_id: str
    title: str
    page: int | None = None


class AttachmentOut(CamelModel):
    url: str
    type: Literal["image", "pdf"]
    source: Literal["camera", "library", "files"]


class MessageOut(CamelModel):
    id: str
    thread_id: str
    role: Literal["student", "teacher", "nudge"]
    content: str
    attachment: AttachmentOut | None = None
    citations: list[CitationOut]
    created_at: datetime


class FlagOut(CamelModel):
    id: str
    message_id: str
    course_id: str
    assignment_title: str | None = None
    flag_count: int
    status: Literal["open", "resolved"]
    correction: str | None = None
    created_at: datetime


class CourseSettingsOut(CamelModel):
    hints_only: bool
    use_solution_keys: bool
    cite_materials: bool
    deadline_reminders: bool


class ErrorOut(BaseModel):
    error: str
    message: str
