C272 = "c0000000-0272-4000-8000-000000000001"
C213 = "c0000000-0213-4000-8000-00000000000a"  # Prof. K's; Sam is enrolled, Alex is not
PS4 = "b0000000-0004-4000-8000-000000000001"
PS4_SOLUTIONS = "d0000000-0004-4000-8000-000000000004"
PROBLEM_3 = "e0000000-0003-4000-8000-000000000001"
ALEX_THREAD = "e0000000-0000-4000-8000-000000000005"
PROF_H_THREAD = "e0000000-0000-4000-8000-000000000007"


def send(client, headers, thread_id, content="", attachment=None, source=None):
    data = {"content": content}
    if source:
        data["attachmentSource"] = source
    files = {"attachment": attachment} if attachment else None
    return client.post(f"/threads/{thread_id}/messages", headers=headers, data=data, files=files)


# ---- students ----


def test_threads_are_newest_first_and_searchable(client, sam):
    threads = client.get("/threads", headers=sam).json()["threads"]
    assert [t["title"] for t in threads][:2] == ["Problem 3", "Lab 3 setup"]
    assert {t["ownerRole"] for t in threads} == {"student"}
    found = client.get("/threads?q=lecture", headers=sam).json()["threads"]
    assert [t["title"] for t in found] == ["Lecture 6 review"]


def test_cannot_open_someone_elses_thread(client, sam):
    assert client.get(f"/threads/{ALEX_THREAD}", headers=sam).status_code == 404
    assert client.get(f"/threads/{PROF_H_THREAD}", headers=sam).status_code == 404


def test_student_needs_enrollment(client, alex):
    assert client.post("/threads", headers=alex, json={"courseId": C213}).status_code == 404


def test_chat_flow(client, sam):
    created = client.post("/threads", headers=sam, json={"courseId": C272, "assignmentId": PS4}).json()["thread"]
    assert created["title"] == "Problem Set 4"
    assert created["ownerRole"] == "student"

    sent = send(client, sam, created["id"], "How do I use substitution on problem 3?")
    assert sent.status_code == 201
    assert sent.json()["sentMessage"]["role"] == "student"
    reply = sent.json()["reply"]
    assert reply["role"] == "nudge"
    assert reply["citations"], "replies cite course materials"
    assert all(c["materialId"] != PS4_SOLUTIONS for c in reply["citations"])

    thread = client.get(f"/threads/{created['id']}", headers=sam).json()
    assert [m["role"] for m in thread["messages"]] == ["student", "nudge"]
    newest = client.get("/threads", headers=sam).json()["threads"][0]
    assert newest["id"] == created["id"]


def test_empty_message_is_rejected(client, sam):
    assert send(client, sam, PROBLEM_3, " ").status_code == 400


def test_hints_only_off_changes_reply(client, sam, prof_h):
    client.patch(f"/teacher/courses/{C272}/settings", headers=prof_h, json={"hintsOnly": False})
    reply = send(client, sam, PROBLEM_3, "substitution").json()["reply"]
    assert "covers this" in reply["content"]


# ---- attachments ----


def test_photo_attachment(client, sam):
    sent = send(client, sam, PROBLEM_3, attachment=("work.png", b"png-bytes", "image/png"), source="camera")
    attachment = sent.json()["sentMessage"]["attachment"]
    assert attachment["type"] == "image"
    assert attachment["source"] == "camera"
    assert ".png" in attachment["url"]


def test_pdf_attachment_is_not_a_course_material(client, sam, prof_h):
    before = client.get(f"/teacher/courses/{C272}", headers=prof_h).json()["course"]["materialCount"]
    sent = send(client, sam, PROBLEM_3, "Is my work right?", ("work.pdf", b"%PDF-1.4", "application/pdf"), "files")
    assert sent.status_code == 201
    attachment = sent.json()["sentMessage"]["attachment"]
    assert (attachment["type"], attachment["source"]) == ("pdf", "files")
    assert ".pdf" in attachment["url"]
    after = client.get(f"/teacher/courses/{C272}", headers=prof_h).json()["course"]["materialCount"]
    assert after == before


def test_attachment_needs_a_source(client, sam):
    response = send(client, sam, PROBLEM_3, attachment=("work.png", b"png", "image/png"))
    assert response.status_code == 400
    assert response.json()["error"] == "missing_source"


def test_attachment_must_be_image_or_pdf(client, sam):
    response = send(client, sam, PROBLEM_3, attachment=("notes.docx", b"doc", "application/msword"), source="files")
    assert response.status_code == 400
    assert response.json()["error"] == "unsupported_file"


# ---- teachers ----


def test_teacher_sees_only_their_own_chats(client, prof_h):
    threads = client.get("/threads", headers=prof_h).json()["threads"]
    assert [(t["title"], t["ownerRole"]) for t in threads] == [("PS 4 rubric", "teacher")]


def test_teacher_chats_in_a_course_they_teach(client, prof_h):
    created = client.post("/threads", headers=prof_h, json={"courseId": C272, "title": "Grading"})
    assert created.status_code == 201
    assert created.json()["thread"]["ownerRole"] == "teacher"
    sent = send(client, prof_h, created.json()["thread"]["id"], "How should I grade substitution?")
    assert sent.json()["sentMessage"]["role"] == "teacher"


def test_teacher_cannot_chat_in_another_teachers_course(client, prof_h):
    assert client.post("/threads", headers=prof_h, json={"courseId": C213}).status_code == 404


def test_hints_only_does_not_apply_to_teachers(client, prof_h):
    # C272 has "hints only" on; a student would get a hint here.
    reply = send(client, prof_h, PROF_H_THREAD, "substitution").json()["reply"]
    assert "covers this" in reply["content"]


def test_teacher_questions_are_not_in_dashboard_counts(client, prof_h):
    before = client.get(f"/teacher/courses/{C272}/dashboard", headers=prof_h).json()["stats"]
    send(client, prof_h, PROF_H_THREAD, "Another question")
    after = client.get(f"/teacher/courses/{C272}/dashboard", headers=prof_h).json()["stats"]
    assert after == before
