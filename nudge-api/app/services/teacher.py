"""Everything a teacher can do. One method per /teacher endpoint."""

import secrets
from dataclasses import replace
from datetime import timedelta

from app.config import Settings
from app.domain import Assignment, Course, CourseSettings, Material, MaterialKind, User
from app.errors import ApiError, bad_request, not_found
from app.integrations.storage import StorageClient
from app.repositories.base import Repository
from app.schemas.teacher import (
    CanvasImportRequest,
    CopyFrom,
    CourseStatsOut,
    DashboardResponse,
    MaterialResponse,
    NotificationsResponse,
    SemesterGroupOut,
    SettingsResponse,
    TeacherCourseDetailResponse,
    TeacherCourseResponse,
    TeacherCoursesResponse,
    TeacherMeResponse,
    TeacherNotifications,
    TeacherStatsOut,
    TeacherUserOut,
    TrendingTopicOut,
)
from app.services.common import new_id, semester_sort_key, semester_start, utc_now
from app.services.views import Views

JOIN_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I
JOIN_CODE_LENGTH = 6
ACTIVITY_WINDOW = timedelta(days=7)
TRENDING_LIMIT = 5
ALLOWED_UPLOADS = {"application/pdf", "image/jpeg", "image/png", "image/heic", "image/webp"}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class TeacherService:
    def __init__(self, repo: Repository, storage: StorageClient, views: Views, settings: Settings):
        self.repo = repo
        self.storage = storage
        self.views = views
        self.settings = settings

    def _own_course(self, teacher: User, course_id: str) -> Course:
        course = self.repo.get_course(course_id)
        if not course or course.teacher_id != teacher.id:
            raise not_found("Course")
        return course

    # ---- profile ----

    def get_me(self, teacher: User) -> TeacherMeResponse:
        courses = self.repo.list_courses_for_teacher(teacher.id)
        current = [c for c in courses if c.semester == self.settings.current_semester]
        return TeacherMeResponse(
            user=TeacherUserOut(
                id=teacher.id,
                name=teacher.name,
                email=teacher.email,
                role=teacher.role,
                department=teacher.department,
            ),
            stats=TeacherStatsOut(
                sections_now=len(current),
                students=sum(self.repo.count_students(c.id) for c in current),
                semesters=len({c.semester for c in courses}),
            ),
            notifications=TeacherNotifications.model_validate(teacher.notifications),
        )

    def update_notifications(self, teacher: User, changes: TeacherNotifications) -> NotificationsResponse:
        updated = self.repo.update_user_notifications(
            teacher.id, changes.model_dump(by_alias=True, exclude_none=True)
        )
        return NotificationsResponse(notifications=TeacherNotifications.model_validate(updated))

    # ---- courses ----

    def list_courses(self, teacher: User) -> TeacherCoursesResponse:
        groups: dict[str, list[Course]] = {}
        for course in self.repo.list_courses_for_teacher(teacher.id):
            groups.setdefault(course.semester, []).append(course)
        semesters = [
            SemesterGroupOut(
                name=name,
                is_current=name == self.settings.current_semester,
                courses=[
                    self.views.course(c)
                    for c in sorted(groups[name], key=lambda c: (c.code, c.section))
                ],
            )
            for name in sorted(groups, key=semester_sort_key, reverse=True)
        ]
        return TeacherCoursesResponse(semesters=semesters)

    def create_course(
        self, teacher: User, code: str, section: str, semester: str, copy_from: CopyFrom | None
    ) -> TeacherCourseResponse:
        code, section, semester = code.strip(), section.strip(), semester.strip()
        if not code or not section or not semester:
            raise bad_request("missing_fields", "Course code, section and semester are required.")
        try:
            semester_start(semester)
        except ValueError:
            raise bad_request("invalid_semester", "Semester should look like 'Fall 2026'.")

        source = self._own_course(teacher, copy_from.course_id) if copy_from else None
        course = self.repo.create_course(
            Course(
                id=new_id(),
                code=code,
                section=section,
                semester=semester,
                teacher_id=teacher.id,
                join_code=self._new_join_code(),
                settings=replace(source.settings) if source and copy_from.settings else CourseSettings(),
                office_hours=source.office_hours if source else None,
            )
        )
        if source:
            self._copy_course_content(source, course, copy_from)
        return TeacherCourseResponse(course=self.views.teacher_course(course))

    def _new_join_code(self) -> str:
        while True:
            code = "".join(secrets.choice(JOIN_CODE_ALPHABET) for _ in range(JOIN_CODE_LENGTH))
            if not self.repo.get_course_by_join_code(code):
                return code

    def _copy_course_content(self, source: Course, target: Course, options: CopyFrom) -> None:
        material_ids: dict[str, str] = {}
        if options.materials:
            for material in self.repo.list_materials(source.id, include_restricted=True):
                material_ids[material.id] = self._copy_material(material, target)

        shift = semester_start(target.semester) - semester_start(source.semester)
        for assignment in self.repo.list_assignments(source.id):
            due_at = assignment.due_at + shift if assignment.due_at and options.shift_deadlines else None
            self.repo.create_assignment(
                Assignment(
                    id=new_id(),
                    course_id=target.id,
                    title=assignment.title,
                    short_title=assignment.short_title,
                    material_id=material_ids.get(assignment.material_id or ""),
                    due_at=due_at,
                )
            )

    def _copy_material(self, material: Material, target: Course) -> str:
        new_material_id = new_id()
        folder = "restricted" if material.restricted else "materials"
        path = f"courses/{target.id}/{folder}/{new_material_id}/{material.title}"
        self.storage.copy(material.storage_path, path)
        self.repo.create_material(
            replace(material, id=new_material_id, course_id=target.id, storage_path=path,
                    uploaded_at=utc_now())
        )
        self.repo.add_chunks(
            [
                replace(chunk, id=new_id(), course_id=target.id, material_id=new_material_id)
                for chunk in self.repo.list_chunks(material.id)
            ]
        )
        return new_material_id

    def get_course(self, teacher: User, course_id: str) -> TeacherCourseDetailResponse:
        course = self._own_course(teacher, course_id)
        return TeacherCourseDetailResponse(
            course=self.views.teacher_course(course),
            settings=self.views.settings_out(course),
            materials=[
                self.views.material(m) for m in self.repo.list_materials(course.id, include_restricted=True)
            ],
        )

    def update_settings(self, teacher: User, course_id: str, changes: dict[str, bool]) -> SettingsResponse:
        course = self._own_course(teacher, course_id)
        if changes:
            course.settings = self.repo.update_course_settings(course.id, changes)
        return SettingsResponse(settings=self.views.settings_out(course))

    def upload_material(
        self,
        teacher: User,
        course_id: str,
        filename: str,
        data: bytes,
        content_type: str | None,
        kind: MaterialKind,
        restricted: bool,
    ) -> MaterialResponse:
        course = self._own_course(teacher, course_id)
        if content_type not in ALLOWED_UPLOADS:
            raise bad_request("unsupported_file", "Upload a PDF or a photo.")
        if not data:
            raise bad_request("empty_file", "That file is empty.")
        if len(data) > MAX_UPLOAD_BYTES:
            raise bad_request("file_too_large", "Files can be up to 50 MB.")

        material_id = new_id()
        folder = "restricted" if restricted else "materials"
        path = f"courses/{course.id}/{folder}/{material_id}/{filename}"
        self.storage.upload(path, data, content_type)
        material = self.repo.create_material(
            Material(
                id=material_id,
                course_id=course.id,
                title=filename,
                kind=kind,
                size_bytes=len(data),
                storage_path=path,
                restricted=restricted,
                status="processing",
                uploaded_at=utc_now(),
            )
        )
        return MaterialResponse(material=self.views.material(material))

    def dashboard(self, teacher: User, course_id: str) -> DashboardResponse:
        course = self._own_course(teacher, course_id)
        questions, students = self.repo.course_activity(course.id, utc_now() - ACTIVITY_WINDOW)
        flags = self.repo.list_open_flags(course.id)
        return DashboardResponse(
            stats=CourseStatsOut(question_count=questions, active_students=students, flagged_count=len(flags)),
            trending=[
                TrendingTopicOut(id=t.id, title=t.title, student_count=t.student_count)
                for t in self.repo.list_trending_topics(course.id, TRENDING_LIMIT)
            ],
            needs_review=[self.views.flag(f) for f in flags],
        )

    def canvas_import(self, teacher: User, course_id: str, options: CanvasImportRequest) -> None:
        """Version 2. Will pull the syllabus and files in as materials (then
        process them like uploads) and deadlines in as assignments."""
        self._own_course(teacher, course_id)
        raise ApiError(501, "not_implemented", "Canvas import is planned for version 2.")
