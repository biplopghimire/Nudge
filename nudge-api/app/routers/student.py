"""/student endpoints. Each one checks the token belongs to a student, then
hands off to StudentService. Chats are shared with teachers, in routers/threads.py."""

from fastapi import APIRouter, Depends, Query

from app.deps import current_student, get_student_service
from app.domain import User
from app.schemas.student import (
    FlagRequest,
    FlagResponse,
    JoinCourseRequest,
    JoinCourseResponse,
    MaterialLinkResponse,
    NotificationsResponse,
    StudentCourseResponse,
    StudentCoursesResponse,
    StudentMeResponse,
    UpdateStudentMeRequest,
)
from app.services.student import StudentService

router = APIRouter(prefix="/student", tags=["student"])

Student = Depends(current_student)
Service = Depends(get_student_service)


@router.get("/me", response_model=StudentMeResponse)
def get_me(student: User = Student, service: StudentService = Service):
    """The signed-in student, their stats and their notification switches."""
    return service.get_me(student)


@router.patch("/me", response_model=NotificationsResponse)
def update_me(body: UpdateStudentMeRequest, student: User = Student, service: StudentService = Service):
    """Turn notification switches on or off. Send only the ones that changed."""
    return service.update_notifications(student, body.notifications)


@router.get("/courses", response_model=StudentCoursesResponse)
def list_courses(student: User = Student, service: StudentService = Service):
    """The Up next assignment and the student's courses with due badges."""
    return service.list_courses(student)


@router.post("/courses/join", response_model=JoinCourseResponse, status_code=201)
def join_course(body: JoinCourseRequest, student: User = Student, service: StudentService = Service):
    """Join a course with the 6-character code from the teacher."""
    return service.join_course(student, body.join_code)


@router.get("/courses/{course_id}", response_model=StudentCourseResponse)
def get_course(course_id: str, student: User = Student, service: StudentService = Service):
    """One course and its materials. Restricted files are never included."""
    return service.get_course(student, course_id)


@router.get("/materials/{material_id}/link", response_model=MaterialLinkResponse)
def material_link(
    material_id: str,
    page: int | None = Query(None, ge=1, description="Page to open, from the citation"),
    student: User = Student,
    service: StudentService = Service,
):
    """A temporary link (15 minutes) to open a file."""
    return service.material_link(student, material_id, page)


@router.post("/messages/{message_id}/flag", response_model=FlagResponse, status_code=201)
def flag_message(
    message_id: str, body: FlagRequest, student: User = Student, service: StudentService = Service
):
    """Report a Nudge reply. The teacher sees it under Needs your review."""
    return service.flag_message(student, message_id, body.reason, body.note)
