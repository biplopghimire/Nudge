from app.schemas.common import (
    CamelModel,
    CourseOut,
    CourseSettingsOut,
    FlagOut,
    MaterialOut,
    TeacherCourseOut,
    UserOut,
)


class TeacherUserOut(UserOut):
    department: str | None = None


class TeacherStatsOut(CamelModel):
    sections_now: int
    students: int
    semesters: int


class TeacherNotifications(CamelModel):
    flagged_answers: bool | None = None
    weekly_digest: bool | None = None


class TeacherMeResponse(CamelModel):
    user: TeacherUserOut
    stats: TeacherStatsOut
    notifications: TeacherNotifications


class UpdateTeacherMeRequest(CamelModel):
    notifications: TeacherNotifications


class NotificationsResponse(CamelModel):
    notifications: TeacherNotifications


class SemesterGroupOut(CamelModel):
    name: str
    is_current: bool
    courses: list[CourseOut]


class TeacherCoursesResponse(CamelModel):
    semesters: list[SemesterGroupOut]


class CopyFrom(CamelModel):
    course_id: str
    materials: bool = True
    settings: bool = True
    shift_deadlines: bool = True


class CreateCourseRequest(CamelModel):
    code: str
    section: str
    semester: str
    copy_from: CopyFrom | None = None


class TeacherCourseResponse(CamelModel):
    course: TeacherCourseOut


class TeacherCourseDetailResponse(CamelModel):
    course: TeacherCourseOut
    settings: CourseSettingsOut
    materials: list[MaterialOut]


class UpdateCourseSettingsRequest(CamelModel):
    hints_only: bool | None = None
    use_solution_keys: bool | None = None
    cite_materials: bool | None = None
    deadline_reminders: bool | None = None


class SettingsResponse(CamelModel):
    settings: CourseSettingsOut


class MaterialResponse(CamelModel):
    material: MaterialOut


class CanvasImportRequest(CamelModel):
    syllabus: bool = True
    files: bool = True
    deadlines: bool = True


class CourseStatsOut(CamelModel):
    question_count: int
    active_students: int
    flagged_count: int


class TrendingTopicOut(CamelModel):
    id: str
    title: str
    student_count: int


class DashboardResponse(CamelModel):
    stats: CourseStatsOut
    trending: list[TrendingTopicOut]
    needs_review: list[FlagOut]
