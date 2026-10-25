"""Example data loaded into the in-memory repository on startup.

IDs match the example JSON in nudge-api/shared, student and teacher so the
docs and the mock agree. Dates are relative to server start so "Up next",
"Today" and "This week" always have something to show.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from app.domain import (
    Assignment,
    Chunk,
    Citation,
    Course,
    CourseSettings,
    Flag,
    Material,
    Message,
    Thread,
    TrendingTopic,
    User,
)

SAM = "a0000000-0000-4000-8000-000000000001"
PROF_H = "a0000000-0000-4000-8000-000000000002"
PROF_K = "a0000000-0000-4000-8000-000000000003"
ALEX = "a0000000-0000-4000-8000-000000000004"
PRIYA = "a0000000-0000-4000-8000-000000000005"

C272 = "c0000000-0272-4000-8000-000000000001"
C272_SEC2 = "c0000000-0272-4000-8000-000000000002"
C213 = "c0000000-0213-4000-8000-00000000000a"
C272_S26 = "c0000000-0272-4000-8000-000000000a26"

LECTURE_6 = "d0000000-0006-4000-8000-000000000001"
PS4_FILE = "d0000000-0004-4000-8000-000000000002"
SYLLABUS = "d0000000-0001-4000-8000-000000000003"
PS4_SOLUTIONS = "d0000000-0004-4000-8000-000000000004"

PS4 = "b0000000-0004-4000-8000-000000000001"
LAB3 = "b0000000-0213-4000-8000-000000000003"

PROBLEM_3_THREAD = "e0000000-0003-4000-8000-000000000001"


@dataclass
class SeedData:
    users: list[User] = field(default_factory=list)
    courses: list[Course] = field(default_factory=list)
    enrollments: list[tuple[str, str]] = field(default_factory=list)
    materials: list[Material] = field(default_factory=list)
    assignments: list[Assignment] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    threads: list[Thread] = field(default_factory=list)
    messages: list[Message] = field(default_factory=list)
    flags: list[Flag] = field(default_factory=list)
    trending: list[TrendingTopic] = field(default_factory=list)


def _material(id, course_id, title, kind, size, restricted=False) -> Material:
    folder = "restricted" if restricted else "materials"
    return Material(
        id=id,
        course_id=course_id,
        title=title,
        kind=kind,
        size_bytes=size,
        storage_path=f"courses/{course_id}/{folder}/{id}/{title}",
        restricted=restricted,
        status="ready",
    )


def default_seed(now: datetime | None = None) -> SeedData:
    now = now or datetime.now(UTC)
    ago = lambda **kw: now - timedelta(**kw)  # noqa: E731

    users = [
        User(SAM, "Sam Lee", "samlee@andrew.cmu.edu", "student",
             notifications={"deadlineReminders": True, "studyNudges": False}),
        User(ALEX, "Alex Chen", "alexchen@andrew.cmu.edu", "student",
             notifications={"deadlineReminders": True, "studyNudges": True}),
        User(PRIYA, "Priya Patel", "ppatel@andrew.cmu.edu", "student",
             notifications={"deadlineReminders": False, "studyNudges": False}),
        User(PROF_H, "Prof. H", "profh@cmu.edu", "teacher", department="Information Systems",
             notifications={"flaggedAnswers": True, "weeklyDigest": True}),
        User(PROF_K, "Prof. K", "profk@cmu.edu", "teacher", department="Computer Science",
             notifications={"flaggedAnswers": True, "weeklyDigest": False}),
    ]

    courses = [
        Course(C272, "67-272", "Sec 1", "Fall 2026", PROF_H, "K7M4QX",
               CourseSettings(hints_only=True, use_solution_keys=True, cite_materials=True,
                              deadline_reminders=False),
               office_hours="Tue and Thu, 4:00pm to 5:30pm"),
        Course(C272_SEC2, "67-272", "Sec 2", "Fall 2026", PROF_H, "P3VN8R",
               office_hours="Tue and Thu, 4:00pm to 5:30pm"),
        Course(C213, "15-213", "Sec A", "Fall 2026", PROF_K, "H2QW9D",
               office_hours="Mon and Wed, 2:00pm to 3:00pm"),
        Course(C272_S26, "67-272", "Sec 1", "Spring 2026", PROF_H, "R8TL2M"),
        Course("c0000000-0213-4000-8000-000000000a26", "15-213", "Sec A", "Spring 2026", PROF_H, "W4ZC7J"),
        Course("c0000000-0272-4000-8000-000000000f25", "67-272", "Sec 1", "Fall 2025", PROF_H, "M9DK3P"),
        Course("c0000000-0213-4000-8000-000000000f25", "15-213", "Sec A", "Fall 2025", PROF_H, "B6XN5T"),
        Course("c0000000-0272-4000-8000-000000000a25", "67-272", "Sec 1", "Spring 2025", PROF_H, "F2HQ8V"),
    ]

    enrollments = [(SAM, C272), (SAM, C213), (ALEX, C272), (PRIYA, C272), (ALEX, C272_SEC2)]

    materials = [
        _material(LECTURE_6, C272, "Lecture 6 - Substitution.pdf", "slides", 2_516_582),
        _material(PS4_FILE, C272, "Problem Set 4.pdf", "homework", 317_440),
        _material(SYLLABUS, C272, "Syllabus.pdf", "syllabus", 184_320),
        _material(PS4_SOLUTIONS, C272, "PS 4 Solutions.pdf", "other", 402_112, restricted=True),
        _material("d0000000-0213-4000-8000-000000000005", C213, "Lab 3 Handout.pdf", "homework", 220_160),
        _material("d0000000-0a26-4000-8000-000000000001", C272_S26, "Lecture 1 - Limits.pdf", "slides", 1_830_400),
        _material("d0000000-0a26-4000-8000-000000000002", C272_S26, "Syllabus.pdf", "syllabus", 176_128),
    ]

    assignments = [
        Assignment(PS4, C272, "Problem Set 4", "PS 4", PS4_FILE, due_at=now + timedelta(days=2)),
        Assignment("b0000000-0003-4000-8000-000000000001", C272, "Problem Set 3", "PS 3",
                   due_at=ago(days=9)),
        Assignment(LAB3, C213, "Lab 3", "Lab 3", due_at=now + timedelta(days=5)),
        Assignment("b0000000-0a26-4000-8000-000000000001", C272_S26, "Problem Set 1", "PS 1",
                   due_at=datetime(2026, 1, 30, 23, 59, tzinfo=UTC)),
    ]

    chunks = [
        Chunk("c1000000-0000-4000-8000-000000000001", C272, LECTURE_6,
              "Lecture 6 - Substitution, slide 4. For an integral of a product f(g(x)) g'(x), "
              "let u = g(x), so du = g'(x) dx. Rewrite the integral in terms of u, integrate, "
              "then substitute back to x.", page=4, heading="Slide 4"),
        Chunk("c1000000-0000-4000-8000-000000000002", C272, LECTURE_6,
              "Lecture 6 - Substitution, slide 5. Definite integrals: change the limits of "
              "integration to u-values, or substitute back before evaluating.", page=5, heading="Slide 5"),
        Chunk("c1000000-0000-4000-8000-000000000003", C272, PS4_FILE,
              "Problem Set 4, problem 3. Evaluate the integral of x cos(x^2) dx. "
              "Show your substitution.", page=1, heading="Problem 3"),
        Chunk("c1000000-0000-4000-8000-000000000004", C272, SYLLABUS,
              "Syllabus. Office hours are Tue and Thu, 4:00pm to 5:30pm. Problem sets are due "
              "Thursdays at 11:59pm.", page=1, heading="Course policies"),
        Chunk("c1000000-0000-4000-8000-000000000005", C272, PS4_SOLUTIONS,
              "PS 4 Solutions, problem 3. u = x^2, du = 2x dx, answer (1/2) sin(x^2) + C.",
              page=1, heading="Problem 3", restricted=True),
    ]

    threads = [
        Thread(PROBLEM_3_THREAD, SAM, C272, "Problem 3", ago(hours=1), assignment_id=PS4),
        Thread("e0000000-0000-4000-8000-000000000002", SAM, C213, "Lab 3 setup", ago(hours=2),
               assignment_id=LAB3),
        Thread("e0000000-0000-4000-8000-000000000003", SAM, C272, "Lecture 6 review", ago(days=4)),
        Thread("e0000000-0000-4000-8000-000000000004", SAM, C272, "PS 3 · Question 5", ago(days=6)),
        Thread("e0000000-0000-4000-8000-000000000005", ALEX, C272, "PS 4 · Q2", ago(hours=6),
               assignment_id=PS4),
        Thread("e0000000-0000-4000-8000-000000000006", PRIYA, C272, "Chain rule vs. u-sub", ago(days=1)),
        Thread("e0000000-0000-4000-8000-000000000007", PROF_H, C272, "PS 4 rubric", ago(hours=3),
               assignment_id=PS4, owner_role="teacher"),
    ]

    lecture_6_p4 = Citation(LECTURE_6, "Lecture 6", 4)
    t = threads[0].updated_at
    messages = [
        Message("f0000000-0000-4000-8000-000000000001", PROBLEM_3_THREAD, "student",
                "I'm stuck on the integral in #3", t - timedelta(minutes=2, seconds=36)),
        Message("f0000000-0000-4000-8000-000000000002", PROBLEM_3_THREAD, "nudge",
                "What substitution did lecture 6 suggest for a product like this?",
                t - timedelta(minutes=2, seconds=32), citations=[lecture_6_p4]),
        Message("f0000000-0000-4000-8000-000000000003", PROBLEM_3_THREAD, "student", "",
                t - timedelta(seconds=6), attachment_path=f"uploads/{SAM}/f0000000-0000-4000-8000-000000000003.jpg",
                attachment_type="image", attachment_source="camera"),
        Message("f0000000-0000-4000-8000-000000000004", PROBLEM_3_THREAD, "nudge",
                "Your substitution is right. On the last line, your answer is still in terms of u. "
                "What should it be in terms of?", t,
                citations=[lecture_6_p4, Citation(PS4_FILE, "PS 4", 1)]),
        Message("f0000000-0000-4000-8000-000000000010", "e0000000-0000-4000-8000-000000000002", "student",
                "How do I start the bomb lab?", ago(hours=2, minutes=1)),
        Message("f0000000-0000-4000-8000-000000000011", "e0000000-0000-4000-8000-000000000002", "nudge",
                "The handout's first section walks through setup. Which step are you on?", ago(hours=2)),
        Message("f0000000-0000-4000-8000-000000000098", "e0000000-0000-4000-8000-000000000005", "student",
                "Is the answer to Q2 sin(x^2)?", ago(hours=6, minutes=1)),
        Message("f0000000-0000-4000-8000-000000000099", "e0000000-0000-4000-8000-000000000005", "nudge",
                "Yes, the answer is sin(x^2) + C.", ago(hours=6), citations=[lecture_6_p4]),
        Message("f0000000-0000-4000-8000-000000000012", "e0000000-0000-4000-8000-000000000006", "student",
                "When do I use the chain rule instead of u-substitution?", ago(days=1)),
        Message("f0000000-0000-4000-8000-000000000013", "e0000000-0000-4000-8000-000000000007", "teacher",
                "What mistakes should I watch for when grading problem 3?", ago(hours=3, minutes=1)),
        Message("f0000000-0000-4000-8000-000000000014", "e0000000-0000-4000-8000-000000000007", "nudge",
                "Lecture 6 slide 4 covers this: watch for answers left in terms of u.", ago(hours=3),
                citations=[lecture_6_p4]),
    ]

    flags = [
        Flag("90000000-0000-4000-8000-000000000001", "f0000000-0000-4000-8000-000000000099", C272,
             "gave away answer", ago(hours=5), note="It just told me the answer."),
        Flag("90000000-0000-4000-8000-000000000002", "f0000000-0000-4000-8000-000000000099", C272,
             "wrong answer", ago(hours=4), note="Missing the 1/2."),
    ]

    trending = [
        TrendingTopic("70000000-0000-4000-8000-000000000001", C272, "Substitution in PS 4", 12),
        TrendingTopic("70000000-0000-4000-8000-000000000002", C272, "Chain rule vs. u-sub", 7),
    ]

    return SeedData(users, courses, enrollments, materials, assignments, chunks,
                    threads, messages, flags, trending)
