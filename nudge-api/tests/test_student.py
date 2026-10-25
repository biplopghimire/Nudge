C272 = "c0000000-0272-4000-8000-000000000001"
C213 = "c0000000-0213-4000-8000-00000000000a"
LECTURE_6 = "d0000000-0006-4000-8000-000000000001"
PS4_SOLUTIONS = "d0000000-0004-4000-8000-000000000004"


def test_home_has_up_next_and_badges(client, sam):
    body = client.get("/student/courses", headers=sam).json()
    assert body["upNext"]["title"] == "Problem Set 4"
    assert body["upNext"]["shortTitle"] == "PS 4"
    assert body["upNext"]["courseCode"] == "67-272"
    assert body["courses"][0]["nextDue"].startswith("PS 4 · ")


def test_notifications_update_is_merged(client, sam):
    response = client.patch("/student/me", headers=sam, json={"notifications": {"studyNudges": True}})
    assert response.json()["notifications"] == {"deadlineReminders": True, "studyNudges": True}
    assert client.get("/student/me", headers=sam).json()["notifications"]["studyNudges"] is True


def test_join_course(client, alex):
    response = client.post("/student/courses/join", headers=alex, json={"joinCode": "h2qw9d"})
    assert response.status_code == 201
    codes = [c["code"] for c in client.get("/student/courses", headers=alex).json()["courses"]]
    assert "15-213" in codes


def test_join_with_wrong_code(client, sam):
    response = client.post("/student/courses/join", headers=sam, json={"joinCode": "ZZZZZZ"})
    assert response.status_code == 404
    assert response.json()["error"] == "invalid_code"


def test_join_twice(client, sam):
    response = client.post("/student/courses/join", headers=sam, json={"joinCode": "K7M4QX"})
    assert response.status_code == 409


def test_course_hides_restricted_materials(client, sam):
    materials = client.get(f"/student/courses/{C272}", headers=sam).json()["materials"]
    assert all(not m["restricted"] for m in materials)
    assert PS4_SOLUTIONS not in [m["id"] for m in materials]


def test_course_not_enrolled_is_404(client, alex):
    assert client.get(f"/student/courses/{C213}", headers=alex).status_code == 404


def test_material_link(client, sam):
    body = client.get(f"/student/materials/{LECTURE_6}/link?page=4", headers=sam).json()
    assert body["page"] == 4
    assert "X-Goog-Expires=900" in body["url"]


def test_restricted_material_link_is_404(client, sam):
    assert client.get(f"/student/materials/{PS4_SOLUTIONS}/link", headers=sam).status_code == 404


def test_flag_shows_up_for_teacher(client, sam, prof_h):
    before = client.get(f"/teacher/courses/{C272}/dashboard", headers=prof_h).json()["stats"]["flaggedCount"]
    response = client.post(
        "/student/messages/f0000000-0000-4000-8000-000000000004/flag",
        headers=sam,
        json={"reason": "wrong answer"},
    )
    assert response.status_code == 201
    assert response.json()["flag"]["assignmentTitle"] == "PS 4"
    assert response.json()["officeHours"]
    after = client.get(f"/teacher/courses/{C272}/dashboard", headers=prof_h).json()["stats"]["flaggedCount"]
    assert after == before + 1


def test_cannot_flag_own_message(client, sam):
    response = client.post(
        "/student/messages/f0000000-0000-4000-8000-000000000001/flag", headers=sam, json={"reason": "other"}
    )
    assert response.status_code == 403
