"""/threads endpoints. Any signed-in user; ThreadService checks the role
against the course (enrolled for students, teaching it for teachers)."""

from typing import Literal

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile

from app.deps import current_user, get_thread_service
from app.domain import User
from app.schemas.threads import (
    CreateThreadRequest,
    SendMessageResponse,
    ThreadDetailResponse,
    ThreadResponse,
    ThreadsResponse,
)
from app.services.threads import ThreadService

router = APIRouter(prefix="/threads", tags=["threads"])

CurrentUser = Depends(current_user)
Service = Depends(get_thread_service)


@router.get("", response_model=ThreadsResponse)
def list_threads(
    q: str | None = Query(None, description="Search chat titles"),
    user: User = CurrentUser,
    service: ThreadService = Service,
):
    """Your past chats, newest first."""
    return service.list_threads(user, q)


@router.post("", response_model=ThreadResponse, status_code=201)
def create_thread(body: CreateThreadRequest, user: User = CurrentUser, service: ThreadService = Service):
    """Start a new chat in a course, optionally tied to an assignment."""
    return service.create_thread(user, body.course_id, body.assignment_id, body.title)


@router.get("/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(thread_id: str, user: User = CurrentUser, service: ThreadService = Service):
    """One chat and all its messages, including Nudge's citations."""
    return service.get_thread(user, thread_id)


@router.post("/{thread_id}/messages", response_model=SendMessageResponse, status_code=201)
def send_message(
    thread_id: str,
    content: str = Form(""),
    attachment: UploadFile | None = File(None, description="An image or a PDF"),
    attachment_source: Literal["camera", "library", "files"] | None = Form(None, alias="attachmentSource"),
    user: User = CurrentUser,
    service: ThreadService = Service,
):
    """Send a question, with an optional image or PDF, and get Nudge's reply."""
    data = attachment.file.read() if attachment else None
    return service.send_message(
        user,
        thread_id,
        content,
        data or None,
        attachment.content_type if attachment else None,
        attachment_source,
    )
