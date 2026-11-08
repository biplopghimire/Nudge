"""Turn domain records into API response models.

Kept in one place so student and teacher endpoints describe a course,
material, message or flag the same way.
"""

from datetime import timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.domain import Assignment, Course, Flag, Material, Message, Thread
from app.integrations.storage import StorageClient
from app.repositories.base import Repository
from app.schemas.common import (
    AssignmentOut,
    AttachmentOut,
    ChatThreadOut,
    CitationOut,
    CourseOut,
    CourseSettingsOut,
    CourseSummaryOut,
    FlagOut,
    MaterialOut,
    MessageOut,
    TeacherCourseOut,
)
from app.services.common import utc_now


class Views:
    def __init__(self, repo: Repository, storage: StorageClient, settings: Settings):
        self.repo = repo
        self.storage = storage
        self.settings = settings

    def _teacher_name(self, course: Course) -> str:
        teacher = self.repo.get_user(course.teacher_id)
        return teacher.name if teacher else ""

    def course(self, course: Course) -> CourseOut:
        return CourseOut(
            id=course.id,
            code=course.code,
            section=course.section,
            semester=course.semester,
            teacher_name=self._teacher_name(course),
            material_count=self.repo.count_materials(course.id),
            student_count=self.repo.count_students(course.id),
        )

    def teacher_course(self, course: Course) -> TeacherCourseOut:
        return TeacherCourseOut(**self.course(course).model_dump(), join_code=course.join_code)

    def next_assignment(self, course: Course) -> Assignment | None:
        now = utc_now()
        upcoming = [a for a in self.repo.list_assignments(course.id) if a.due_at and a.due_at >= now]
        return upcoming[0] if upcoming else None

    def course_summary(self, course: Course) -> CourseSummaryOut:
        upcoming = self.next_assignment(course)
        next_due = None
        if upcoming:
            weekday = upcoming.due_at.astimezone(ZoneInfo(self.settings.timezone)).strftime("%a")
            next_due = f"{upcoming.short_title or upcoming.title} · {weekday}"
        return CourseSummaryOut(
            id=course.id,
            code=course.code,
            section=course.section,
            teacher_name=self._teacher_name(course),
            next_due=next_due,
            current_assignment_title=upcoming.title if upcoming else None,
        )

    def assignment(self, assignment: Assignment, course: Course) -> AssignmentOut:
        return AssignmentOut(
            id=assignment.id,
            course_id=assignment.course_id,
            course_code=course.code,
            title=assignment.title,
            short_title=assignment.short_title or assignment.title,
            due_at=assignment.due_at,
        )

    def material(self, material: Material) -> MaterialOut:
        return MaterialOut(
            id=material.id,
            course_id=material.course_id,
            title=material.title,
            kind=material.kind,
            size_bytes=material.size_bytes,
            restricted=material.restricted,
            status=material.status,
            progress=100 if material.status == "ready" else material.progress,
            stage=material.stage if material.status == "processing" else None,
            eta_seconds=self._eta(material),
            error=material.error if material.status == "failed" else None,
        )

    @staticmethod
    def _eta(material: Material) -> int | None:
        """Time left, from how long it has taken so far. Only once there's enough to go on."""
        if material.status != "processing" or not material.processing_started_at or material.progress < 5:
            return None
        elapsed = (utc_now() - material.processing_started_at).total_seconds()
        return max(1, round(elapsed * (100 - material.progress) / material.progress))

    def thread(self, thread: Thread) -> ChatThreadOut:
        course = self.repo.get_course(thread.course_id)
        return ChatThreadOut(
            id=thread.id,
            course_id=thread.course_id,
            course_code=course.code if course else "",
            assignment_id=thread.assignment_id,
            owner_role=thread.owner_role,
            title=thread.title,
            updated_at=thread.updated_at,
        )

    def message(self, message: Message) -> MessageOut:
        attachment = None
        if message.attachment_path:
            url, _ = self.storage.signed_url(
                message.attachment_path, timedelta(minutes=self.settings.signed_url_minutes)
            )
            attachment = AttachmentOut(
                url=url, type=message.attachment_type or "image", source=message.attachment_source or "camera"
            )
        return MessageOut(
            id=message.id,
            thread_id=message.thread_id,
            role=message.role,
            content=message.content,
            attachment=attachment,
            citations=[
                CitationOut(material_id=c.material_id, title=c.title, page=c.page)
                for c in message.citations
            ],
            created_at=message.created_at,
        )

    def flag(self, flag: Flag) -> FlagOut:
        return FlagOut(
            id=flag.id,
            message_id=flag.message_id,
            course_id=flag.course_id,
            assignment_title=self._flag_topic(flag),
            flag_count=self.repo.count_flags_for_message(flag.message_id),
            status=flag.status,
            correction=flag.correction,
            created_at=flag.created_at,
        )

    def _flag_topic(self, flag: Flag) -> str | None:
        message = self.repo.get_message(flag.message_id)
        thread = self.repo.get_thread(message.thread_id) if message else None
        if not thread:
            return None
        assignment = self.repo.get_assignment(thread.assignment_id) if thread.assignment_id else None
        return (assignment.short_title or assignment.title) if assignment else thread.title

    def settings_out(self, course: Course) -> CourseSettingsOut:
        s = course.settings
        return CourseSettingsOut(
            hints_only=s.hints_only,
            use_solution_keys=s.use_solution_keys,
            cite_materials=s.cite_materials,
            deadline_reminders=s.deadline_reminders,
        )
