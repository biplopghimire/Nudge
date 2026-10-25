from datetime import datetime
from typing import Literal

from app.schemas.common import (
    AssignmentOut,
    CamelModel,
    CourseOut,
    CourseSummaryOut,
    FlagOut,
    MaterialOut,
    UserOut,
)


class StudentStatsOut(CamelModel):
    questions_asked: int
    problems_solved: int
    photos_checked: int


class StudentNotifications(CamelModel):
    deadline_reminders: bool | None = None
    study_nudges: bool | None = None


class StudentMeResponse(CamelModel):
    user: UserOut
    stats: StudentStatsOut
    notifications: StudentNotifications


class UpdateStudentMeRequest(CamelModel):
    notifications: StudentNotifications


class NotificationsResponse(CamelModel):
    notifications: StudentNotifications


class StudentCoursesResponse(CamelModel):
    up_next: AssignmentOut | None = None
    courses: list[CourseSummaryOut]


class JoinCourseRequest(CamelModel):
    join_code: str


class JoinCourseResponse(CamelModel):
    course: CourseSummaryOut


class StudentCourseResponse(CamelModel):
    course: CourseOut
    materials: list[MaterialOut]


class MaterialLinkResponse(CamelModel):
    url: str
    page: int | None = None
    expires_at: datetime


class FlagRequest(CamelModel):
    reason: Literal["wrong answer", "gave away answer", "other"]
    note: str | None = None


class FlagResponse(CamelModel):
    flag: FlagOut
    office_hours: str | None = None
