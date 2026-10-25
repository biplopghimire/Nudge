"""Everything a student can do. One method per /student endpoint."""

from datetime import timedelta

from app.config import Settings
from app.domain import Course, Flag, Message, Thread, User
from app.errors import ApiError, bad_request, forbidden, not_found
from app.integrations.storage import StorageClient
from app.repositories.base import Repository
from app.schemas.student import (
    FlagResponse,
    JoinCourseResponse,
    MaterialLinkResponse,
    NotificationsResponse,
    SendMessageResponse,
    StudentCourseResponse,
    StudentCoursesResponse,
    StudentMeResponse,
    StudentNotifications,
    StudentStatsOut,
    ThreadDetailResponse,
    ThreadResponse,
    ThreadsResponse,
)
from app.services.auth import user_out
from app.services.chat import ChatService
from app.services.common import new_id, utc_now
from app.services.views import Views

PHOTO_EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/heic": "heic", "image/webp": "webp"}


class StudentService:
    def __init__(
        self,
        repo: Repository,
        storage: StorageClient,
        chat: ChatService,
        views: Views,
        settings: Settings,
    ):
        self.repo = repo
        self.storage = storage
        self.chat = chat
        self.views = views
        self.settings = settings

    # ---- access checks ----

    def _enrolled_course(self, student: User, course_id: str) -> Course:
        course = self.repo.get_course(course_id)
        if not course or not self.repo.is_enrolled(student.id, course_id):
            raise not_found("Course")
        return course

    def _own_thread(self, student: User, thread_id: str) -> Thread:
        thread = self.repo.get_thread(thread_id)
        if not thread or thread.user_id != student.id:
            raise not_found("Chat")
        return thread

    # ---- profile ----

    def get_me(self, student: User) -> StudentMeResponse:
        return StudentMeResponse(
            user=user_out(student),
            stats=StudentStatsOut(
                questions_asked=self.repo.count_student_messages(student.id),
                problems_solved=self.repo.count_assignment_threads(student.id),
                photos_checked=self.repo.count_student_messages(student.id, with_photo=True),
            ),
            notifications=StudentNotifications.model_validate(student.notifications),
        )

    def update_notifications(self, student: User, changes: StudentNotifications) -> NotificationsResponse:
        updated = self.repo.update_user_notifications(
            student.id, changes.model_dump(by_alias=True, exclude_none=True)
        )
        return NotificationsResponse(notifications=StudentNotifications.model_validate(updated))

    # ---- courses ----

    def list_courses(self, student: User) -> StudentCoursesResponse:
        courses = self.repo.list_courses_for_student(student.id)
        upcoming = [(a, c) for c in courses if (a := self.views.next_assignment(c))]
        up_next = min(upcoming, key=lambda pair: pair[0].due_at, default=None)
        return StudentCoursesResponse(
            up_next=self.views.assignment(*up_next) if up_next else None,
            courses=[self.views.course_summary(c) for c in courses],
        )

    def join_course(self, student: User, join_code: str) -> JoinCourseResponse:
        course = self.repo.get_course_by_join_code(join_code)
        if not course:
            raise ApiError(404, "invalid_code", "No course matches that code. Check it with your teacher.")
        if self.repo.is_enrolled(student.id, course.id):
            raise ApiError(409, "already_joined", "You're already in this course.")
        self.repo.enroll(student.id, course.id)
        return JoinCourseResponse(course=self.views.course_summary(course))

    def get_course(self, student: User, course_id: str) -> StudentCourseResponse:
        course = self._enrolled_course(student, course_id)
        materials = self.repo.list_materials(course.id, include_restricted=False)
        return StudentCourseResponse(
            course=self.views.course(course),
            materials=[self.views.material(m) for m in materials],
        )

    def material_link(self, student: User, material_id: str, page: int | None) -> MaterialLinkResponse:
        material = self.repo.get_material(material_id)
        if not material or material.restricted:
            raise not_found("File")
        self._enrolled_course(student, material.course_id)
        url, expires_at = self.storage.signed_url(
            material.storage_path, timedelta(minutes=self.settings.signed_url_minutes)
        )
        return MaterialLinkResponse(url=url, page=page, expires_at=expires_at)

    # ---- chats ----

    def list_threads(self, student: User, query: str | None) -> ThreadsResponse:
        threads = self.repo.list_threads(student.id, query.strip() if query else None)
        return ThreadsResponse(threads=[self.views.thread(t) for t in threads])

    def create_thread(
        self, student: User, course_id: str, assignment_id: str | None, title: str | None
    ) -> ThreadResponse:
        self._enrolled_course(student, course_id)
        assignment = None
        if assignment_id:
            assignment = self.repo.get_assignment(assignment_id)
            if not assignment or assignment.course_id != course_id:
                raise not_found("Assignment")
        if not title or not title.strip():
            title = assignment.title if assignment else "New chat"
        thread = self.repo.create_thread(
            Thread(
                id=new_id(),
                user_id=student.id,
                course_id=course_id,
                title=title.strip(),
                updated_at=utc_now(),
                assignment_id=assignment_id,
            )
        )
        return ThreadResponse(thread=self.views.thread(thread))

    def get_thread(self, student: User, thread_id: str) -> ThreadDetailResponse:
        thread = self._own_thread(student, thread_id)
        return ThreadDetailResponse(
            thread=self.views.thread(thread),
            messages=[self.views.message(m) for m in self.repo.list_messages(thread.id)],
        )

    def send_message(
        self,
        student: User,
        thread_id: str,
        content: str,
        photo: bytes | None,
        photo_mime: str | None,
    ) -> SendMessageResponse:
        thread = self._own_thread(student, thread_id)
        course = self.repo.get_course(thread.course_id)
        content = content.strip()
        if not content and not photo:
            raise bad_request("empty_message", "Type a question or add a photo.")

        attachment_path = None
        if photo:
            extension = PHOTO_EXTENSIONS.get(photo_mime or "", "jpg")
            attachment_path = f"uploads/{student.id}/{new_id()}.{extension}"
            self.storage.upload(attachment_path, photo, photo_mime)

        history = self.repo.list_messages(thread.id)
        student_message = self.repo.add_message(
            Message(
                id=new_id(),
                thread_id=thread.id,
                role="student",
                content=content,
                created_at=utc_now(),
                attachment_path=attachment_path,
            )
        )
        answer = self.chat.answer(thread, course, content, history, photo, photo_mime)
        reply = self.repo.add_message(
            Message(
                id=new_id(),
                thread_id=thread.id,
                role="nudge",
                content=answer.content,
                created_at=utc_now(),
                citations=answer.citations,
            )
        )
        self.repo.touch_thread(thread.id, reply.created_at)
        return SendMessageResponse(
            student_message=self.views.message(student_message),
            reply=self.views.message(reply),
        )

    def flag_message(self, student: User, message_id: str, reason: str, note: str | None) -> FlagResponse:
        message = self.repo.get_message(message_id)
        thread = self.repo.get_thread(message.thread_id) if message else None
        if not message or not thread or thread.user_id != student.id:
            raise not_found("Message")
        if message.role != "nudge":
            raise forbidden("Only Nudge's replies can be reported.")
        flag = self.repo.add_flag(
            Flag(
                id=new_id(),
                message_id=message.id,
                course_id=thread.course_id,
                reason=reason,
                note=note,
                created_at=utc_now(),
            )
        )
        course = self.repo.get_course(thread.course_id)
        return FlagResponse(flag=self.views.flag(flag), office_hours=course.office_hours if course else None)
