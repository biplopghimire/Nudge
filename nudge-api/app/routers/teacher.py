"""/teacher endpoints. Each one checks the token belongs to a teacher, then
hands off to TeacherService."""

from typing import get_args
from urllib.parse import unquote

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile

from app.deps import current_teacher, get_ingestion_service, get_teacher_service
from app.domain import MaterialKind, User
from app.errors import bad_request
from app.schemas.teacher import (
    CanvasImportRequest,
    CreateCourseRequest,
    DashboardResponse,
    MaterialResponse,
    NotificationsResponse,
    SettingsResponse,
    TeacherCourseDetailResponse,
    TeacherCourseResponse,
    TeacherCoursesResponse,
    TeacherMeResponse,
    UpdateCourseSettingsRequest,
    UpdateTeacherMeRequest,
)
from app.schemas.student import MaterialLinkResponse
from app.services.ingestion import IngestionService
from app.services.teacher import TeacherService

router = APIRouter(prefix="/teacher", tags=["teacher"])

Teacher = Depends(current_teacher)
Service = Depends(get_teacher_service)


@router.get("/me", response_model=TeacherMeResponse)
def get_me(teacher: User = Teacher, service: TeacherService = Service):
    """The signed-in teacher, their profile counts and notification switches."""
    return service.get_me(teacher)


@router.patch("/me", response_model=NotificationsResponse)
def update_me(body: UpdateTeacherMeRequest, teacher: User = Teacher, service: TeacherService = Service):
    """Turn notification switches on or off. Send only the ones that changed."""
    return service.update_notifications(teacher, body.notifications)


@router.get("/courses", response_model=TeacherCoursesResponse)
def list_courses(teacher: User = Teacher, service: TeacherService = Service):
    """The teacher's courses grouped by semester, newest first."""
    return service.list_courses(teacher)


@router.post("/courses", response_model=TeacherCourseResponse, status_code=201)
def create_course(body: CreateCourseRequest, teacher: User = Teacher, service: TeacherService = Service):
    """Create a course and get its join code. Send copyFrom to reuse a past course."""
    return service.create_course(teacher, body.code, body.section, body.semester, body.copy_from)


@router.get("/courses/{course_id}", response_model=TeacherCourseDetailResponse)
def get_course(course_id: str, teacher: User = Teacher, service: TeacherService = Service):
    """One course with its join code, Nudge settings and all materials."""
    return service.get_course(teacher, course_id)


@router.patch("/courses/{course_id}/settings", response_model=SettingsResponse)
def update_settings(
    course_id: str,
    body: UpdateCourseSettingsRequest,
    teacher: User = Teacher,
    service: TeacherService = Service,
):
    """Change how Nudge helps in this course. Send only the switches that changed."""
    return service.update_settings(teacher, course_id, body.model_dump(exclude_none=True))


@router.post("/courses/{course_id}/materials", response_model=MaterialResponse, status_code=201)
def upload_material(
    course_id: str,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    kind: str = Form("notes"),
    restricted: bool = Form(False, description="Solution keys and rubrics: never shown to students"),
    teacher: User = Teacher,
    service: TeacherService = Service,
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Upload a PDF or photo. It starts as 'processing' and becomes 'ready'."""
    if kind not in get_args(MaterialKind):
        raise bad_request("invalid_kind", f"kind must be one of: {', '.join(get_args(MaterialKind))}")
    response = service.upload_material(
        teacher,
        course_id,
        unquote(file.filename or "") or "Untitled",  # Expo percent-encodes multipart file names
        file.file.read(),
        file.content_type,
        kind,
        restricted,
    )
    background.add_task(ingestion.process_material, response.material.id, file.content_type)
    return response


@router.post("/materials/{material_id}/retry", response_model=MaterialResponse)
def retry_material(
    material_id: str,
    background: BackgroundTasks,
    teacher: User = Teacher,
    service: TeacherService = Service,
    ingestion: IngestionService = Depends(get_ingestion_service),
):
    """Read a file that failed again, without uploading it again."""
    response = service.retry_material(teacher, material_id)
    background.add_task(ingestion.process_material, response.material.id)
    return response


@router.get("/materials/{material_id}/link", response_model=MaterialLinkResponse)
def material_link(
    material_id: str,
    page: int | None = Query(None, ge=1, description="Page to open, from the citation"),
    teacher: User = Teacher,
    service: TeacherService = Service,
):
    """A temporary link (15 minutes) to open one of your course files, from a test chat citation."""
    return service.material_link(teacher, material_id, page)


@router.get("/courses/{course_id}/dashboard", response_model=DashboardResponse)
def dashboard(course_id: str, teacher: User = Teacher, service: TeacherService = Service):
    """Question count, active students, flagged count, trending topics and answers to review."""
    return service.dashboard(teacher, course_id)


@router.post("/courses/{course_id}/canvas/import", status_code=202)
def canvas_import(
    course_id: str, body: CanvasImportRequest, teacher: User = Teacher, service: TeacherService = Service
):
    """Planned for version 2: import the syllabus, files and deadlines from Canvas.
    Returns 501 until then."""
    return service.canvas_import(teacher, course_id, body)
