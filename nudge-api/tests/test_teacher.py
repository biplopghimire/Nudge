C272 = "c0000000-0272-4000-8000-000000000001"
C213 = "c0000000-0213-4000-8000-00000000000a"  # Prof. K's
C272_S26 = "c0000000-0272-4000-8000-000000000a26"


def test_courses_grouped_newest_semester_first(client, prof_h):
    semesters = client.get("/teacher/courses", headers=prof_h).json()["semesters"]
    assert [s["name"] for s in semesters] == ["Fall 2026", "Spring 2026", "Fall 2025", "Spring 2025"]
    assert semesters[0]["isCurrent"] is True


def test_teacher_cannot_see_other_teachers_course(client, prof_h):
    assert client.get(f"/teacher/courses/{C213}", headers=prof_h).status_code == 404


def test_create_course_and_student_joins(client, prof_h, alex):
    course = client.post(
        "/teacher/courses", headers=prof_h, json={"code": "67-443", "section": "A", "semester": "Fall 2026"}
    ).json()["course"]
    assert len(course["joinCode"]) == 6
    assert course["studentCount"] == 0

    client.post("/student/courses/join", headers=alex, json={"joinCode": course["joinCode"]})
    detail = client.get(f"/teacher/courses/{course['id']}", headers=prof_h).json()
    assert detail["course"]["studentCount"] == 1


def test_create_course_bad_semester(client, prof_h):
    response = client.post(
        "/teacher/courses", headers=prof_h, json={"code": "67-443", "section": "A", "semester": "Autumn"}
    )
    assert response.status_code == 400


def test_reuse_past_course(client, prof_h):
    course = client.post(
        "/teacher/courses",
        headers=prof_h,
        json={
            "code": "67-272",
            "section": "Sec 3",
            "semester": "Spring 2027",
            "copyFrom": {"courseId": C272_S26, "materials": True, "settings": True, "shiftDeadlines": True},
        },
    ).json()["course"]
    assert course["materialCount"] == 2


def test_update_settings(client, prof_h):
    response = client.patch(f"/teacher/courses/{C272}/settings", headers=prof_h, json={"hintsOnly": False})
    assert response.json()["settings"]["hintsOnly"] is False
    assert response.json()["settings"]["useSolutionKeys"] is True
    detail = client.get(f"/teacher/courses/{C272}", headers=prof_h).json()
    assert detail["settings"]["hintsOnly"] is False


def test_upload_is_processing_then_ready(client, prof_h):
    response = client.post(
        f"/teacher/courses/{C272}/materials",
        headers=prof_h,
        files={"file": ("Lecture 7.pdf", b"%PDF-1.4 mock", "application/pdf")},
        data={"type": "slides"},
    )
    assert response.status_code == 201
    material = response.json()["material"]
    assert material["status"] == "processing"

    materials = client.get(f"/teacher/courses/{C272}", headers=prof_h).json()["materials"]
    assert next(m for m in materials if m["id"] == material["id"])["status"] == "ready"


def test_solution_key_upload_is_restricted(client, prof_h):
    material = client.post(
        f"/teacher/courses/{C272}/materials",
        headers=prof_h,
        files={"file": ("PS 5 Solutions.pdf", b"%PDF", "application/pdf")},
        data={"type": "solution_key"},
    ).json()["material"]
    assert material["restricted"] is True


def test_upload_rejects_other_file_types(client, prof_h):
    response = client.post(
        f"/teacher/courses/{C272}/materials",
        headers=prof_h,
        files={"file": ("notes.docx", b"doc", "application/msword")},
    )
    assert response.status_code == 400


def test_dashboard(client, prof_h):
    body = client.get(f"/teacher/courses/{C272}/dashboard", headers=prof_h).json()
    assert body["stats"]["activeStudents"] >= 1
    assert body["trending"][0]["title"] == "Substitution in PS 4"
    assert body["needsReview"][0]["flagCount"] == 2


def test_teacher_profile_counts(client, prof_h):
    stats = client.get("/teacher/me", headers=prof_h).json()["stats"]
    assert stats == {"sectionsNow": 2, "students": 4, "semesters": 4}
