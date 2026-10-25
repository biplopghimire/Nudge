"""Chats, for students and teachers. One method per /threads endpoint.

Students chat in courses they are enrolled in, teachers in courses they teach.
Each thread records its owner's role: "hints only" applies to student threads
only, and teacher threads are left out of dashboard counts.
"""

from app.domain import AttachmentSource, Course, Message, Thread, User
from app.errors import bad_request, not_found
from app.integrations.storage import StorageClient
from app.repositories.base import Repository
from app.schemas.threads import SendMessageResponse, ThreadDetailResponse, ThreadResponse, ThreadsResponse
from app.services.chat import ChatService
from app.services.common import new_id, utc_now
from app.services.views import Views

ATTACHMENT_EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/heic": "heic",
    "image/webp": "webp",
    "application/pdf": "pdf",
}
MAX_ATTACHMENT_BYTES = 20 * 1024 * 1024


class ThreadService:
    def __init__(self, repo: Repository, storage: StorageClient, chat: ChatService, views: Views):
        self.repo = repo
        self.storage = storage
        self.chat = chat
        self.views = views

    # ---- access checks ----

    def _course_for(self, user: User, course_id: str) -> Course:
        course = self.repo.get_course(course_id)
        if user.role == "teacher":
            allowed = course is not None and course.teacher_id == user.id
        else:
            allowed = course is not None and self.repo.is_enrolled(user.id, course_id)
        if not allowed:
            raise not_found("Course")
        return course

    def _own_thread(self, user: User, thread_id: str) -> Thread:
        thread = self.repo.get_thread(thread_id)
        if not thread or thread.user_id != user.id:
            raise not_found("Chat")
        return thread

    # ---- chats ----

    def list_threads(self, user: User, query: str | None) -> ThreadsResponse:
        threads = self.repo.list_threads(user.id, query.strip() if query else None)
        return ThreadsResponse(threads=[self.views.thread(t) for t in threads])

    def create_thread(
        self, user: User, course_id: str, assignment_id: str | None, title: str | None
    ) -> ThreadResponse:
        self._course_for(user, course_id)
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
                user_id=user.id,
                course_id=course_id,
                title=title.strip(),
                updated_at=utc_now(),
                assignment_id=assignment_id,
                owner_role=user.role,
            )
        )
        return ThreadResponse(thread=self.views.thread(thread))

    def get_thread(self, user: User, thread_id: str) -> ThreadDetailResponse:
        thread = self._own_thread(user, thread_id)
        return ThreadDetailResponse(
            thread=self.views.thread(thread),
            messages=[self.views.message(m) for m in self.repo.list_messages(thread.id)],
        )

    def send_message(
        self,
        user: User,
        thread_id: str,
        content: str,
        attachment: bytes | None,
        attachment_mime: str | None,
        attachment_source: AttachmentSource | None,
    ) -> SendMessageResponse:
        thread = self._own_thread(user, thread_id)
        course = self.repo.get_course(thread.course_id)
        content = content.strip()
        if not content and not attachment:
            raise bad_request("empty_message", "Type a question or add a photo or PDF.")

        attachment_path = attachment_type = None
        if attachment:
            extension = ATTACHMENT_EXTENSIONS.get(attachment_mime or "")
            if not extension:
                raise bad_request("unsupported_file", "Attach a photo or a PDF.")
            if len(attachment) > MAX_ATTACHMENT_BYTES:
                raise bad_request("file_too_large", "Attachments can be up to 20 MB.")
            if not attachment_source:
                raise bad_request("missing_source", "Say where the attachment came from: camera, library or files.")
            attachment_type = "pdf" if extension == "pdf" else "image"
            # Saved for the chat history only. It is not chunked, embedded or
            # added to the course materials.
            attachment_path = f"uploads/{user.id}/{new_id()}.{extension}"
            self.storage.upload(attachment_path, attachment, attachment_mime)

        history = self.repo.list_messages(thread.id)
        sent = self.repo.add_message(
            Message(
                id=new_id(),
                thread_id=thread.id,
                role=user.role,
                content=content,
                created_at=utc_now(),
                attachment_path=attachment_path,
                attachment_type=attachment_type,
                attachment_source=attachment_source if attachment else None,
            )
        )
        answer = self.chat.answer(thread, course, content, history, attachment, attachment_mime)
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
        return SendMessageResponse(sent_message=self.views.message(sent), reply=self.views.message(reply))
