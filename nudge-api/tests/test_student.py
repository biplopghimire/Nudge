C272 = "c0000000-0272-4000-8000-000000000001"
C213 = "c0000000-0213-4000-8000-00000000000a"
PS4 = "b0000000-0004-4000-8000-000000000001"
LECTURE_6 = "d0000000-0006-4000-8000-000000000001"
PS4_SOLUTIONS = "d0000000-0004-4000-8000-000000000004"
PROBLEM_3 = "e0000000-0003-4000-8000-000000000001"
ALEX_THREAD = "e0000000-0000-4000-8000-000000000005"


def test_home_has_up_next_and_badges(client, sam):
    body = client.get("/student/courses", headers=sam).json()
    assert body["upNext"]["title"] == "Problem Set 4"
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


def test_threads_are_newest_first_and_searchable(client, sam):
    threads = client.get("/student/threads", headers=sam).json()["threads"]
    assert [t["title"] for t in threads][:2] == ["Problem 3", "Lab 3 setup"]
    found = client.get("/student/threads?q=lecture", headers=sam).json()["threads"]
    assert [t["title"] for t in found] == ["Lecture 6 review"]


def test_cannot_open_someone_elses_thread(client, sam):
    assert client.get(f"/student/threads/{ALEX_THREAD}", headers=sam).status_code == 404


def test_chat_flow(client, sam):
    created = client.post(
        "/student/threads", headers=sam, json={"courseId": C272, "assignmentId": PS4}
    ).json()["thread"]
    assert created["title"] == "Problem Set 4"

    sent = client.post(
        f"/student/threads/{created['id']}/messages",
        headers=sam,
        data={"content": "How do I use substitution on problem 3?"},
    )
    assert sent.status_code == 201
    reply = sent.json()["reply"]
    assert reply["role"] == "nudge"
    assert reply["citations"], "replies cite course materials"
    assert all(c["materialId"] != PS4_SOLUTIONS for c in reply["citations"])

    thread = client.get(f"/student/threads/{created['id']}", headers=sam).json()
    assert [m["role"] for m in thread["messages"]] == ["student", "nudge"]
    newest = client.get("/student/threads", headers=sam).json()["threads"][0]
    assert newest["id"] == created["id"]


def test_photo_message_gets_attachment_url(client, sam):
    sent = client.post(
        f"/student/threads/{PROBLEM_3}/messages",
        headers=sam,
        files={"photo": ("work.png", b"png-bytes", "image/png")},
    ).json()
    assert ".png" in sent["studentMessage"]["attachmentUrl"]


def test_empty_message_is_rejected(client, sam):
    response = client.post(f"/student/threads/{PROBLEM_3}/messages", headers=sam, data={"content": " "})
    assert response.status_code == 400


def test_hints_only_off_changes_reply(client, sam, prof_h):
    client.patch(f"/teacher/courses/{C272}/settings", headers=prof_h, json={"hintsOnly": False})
    reply = client.post(
        f"/student/threads/{PROBLEM_3}/messages", headers=sam, data={"content": "substitution"}
    ).json()["reply"]
    assert "covers this" in reply["content"]


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
