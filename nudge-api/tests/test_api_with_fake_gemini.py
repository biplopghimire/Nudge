"""The whole API running on the real GeminiClient, pointed at a fake Gemini.

This covers the code path production uses (NUDGE_AI=gemini) end to end, with
mock data and no network.
"""

import httpx
import pytest

from tests.fakes import FakeGemini, error_response, json_response, text_response
from tests.test_threads import C272, PROBLEM_3, PS4_SOLUTIONS, send


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda _: None)


@pytest.fixture
def gemini(client) -> FakeGemini:
    fake = FakeGemini()
    client.app.state.container.ai = fake.client(chat_models=["primary", "backup"])
    return fake


def test_student_question_is_answered_by_gemini(client, sam, gemini):
    gemini.queue("generateContent", json_response({"reply": "Which part is g(x)?", "sources": [1]}))
    response = send(client, sam, PROBLEM_3, "How do I use substitution on problem 3?")

    assert response.status_code == 201
    reply = response.json()["reply"]
    assert reply["content"] == "Which part is g(x)?"
    assert len(reply["citations"]) == 1

    [question_embedding] = gemini.calls_to("batchEmbedContents")
    assert question_embedding.body["requests"][0]["taskType"] == "RETRIEVAL_QUERY"
    [call] = gemini.calls_to("generateContent")
    prompt = call.body["contents"][-1]["parts"][0]["text"]
    assert "How do I use substitution on problem 3?" in prompt
    assert "PS 4 Solutions" not in prompt, "solution keys need the student's own work"
    assert "HINTS ONLY" in call.body["systemInstruction"]["parts"][0]["text"]


def test_earlier_chat_is_sent_as_history(client, sam, gemini):
    send(client, sam, PROBLEM_3, "Is my answer right?")
    roles = [c["role"] for c in gemini.calls_to("generateContent")[0].body["contents"]]
    assert roles == ["user", "model", "user", "model", "user"]


def test_restricted_sources_are_never_cited(client, sam, gemini):
    def cite_everything(request):
        assert "RESTRICTED" in request.content.decode(), "a photo lets the solution key be searched"
        body = json_response({"reply": "Check your last line.", "sources": list(range(1, 9))})
        return httpx.Response(200, json=body)

    gemini.queue("generateContent", cite_everything)
    photo = ("work.jpg", b"jpeg", "image/jpeg")
    reply = send(client, sam, PROBLEM_3, attachment=photo, source="camera").json()["reply"]
    assert reply["content"] == "Check your last line."
    assert reply["citations"]
    assert all(c["materialId"] != PS4_SOLUTIONS for c in reply["citations"])


def test_busy_primary_falls_back_to_backup(client, sam, gemini):
    gemini.queue("generateContent", error_response(503, "high demand"))
    response = send(client, sam, PROBLEM_3, "What next?")
    assert response.status_code == 201
    assert [c.model for c in gemini.calls_to("generateContent")] == ["primary", "backup"]


def test_gemini_outage_is_a_503_and_nothing_is_saved(client, sam, gemini):
    gemini.queue("generateContent", *[error_response(503)] * 4)
    before = len(client.get(f"/threads/{PROBLEM_3}", headers=sam).json()["messages"])
    response = send(client, sam, PROBLEM_3, "Hello?")
    assert response.status_code == 503
    assert response.json()["error"] == "nudge_busy"
    assert len(client.get(f"/threads/{PROBLEM_3}", headers=sam).json()["messages"]) == before


def test_new_chat_is_named_by_gemini(client, sam, gemini):
    thread = client.post("/threads", headers=sam, json={"courseId": C272, "title": "New chat"}).json()["thread"]
    # The reply is generated first, then the title.
    gemini.queue("generateContent", json_response(gemini.default_reply), text_response('"Choosing u."'))
    send(client, sam, thread["id"], "how do i know what to pick for u when integrating by parts")
    assert client.get(f"/threads/{thread['id']}", headers=sam).json()["thread"]["title"] == "Choosing u"


def test_new_chat_falls_back_to_the_question_when_gemini_cannot_name_it(client, sam, gemini):
    thread = client.post("/threads", headers=sam, json={"courseId": C272, "title": "New chat"}).json()["thread"]
    gemini.queue("generateContent", json_response(gemini.default_reply), error_response(400, "bad"))
    assert send(client, sam, thread["id"], "When are office hours this week?").status_code == 201
    title = client.get(f"/threads/{thread['id']}", headers=sam).json()["thread"]["title"]
    assert title == "When are office hours this week?"


def test_upload_is_transcribed_and_indexed_by_gemini(client, prof_h, sam, gemini):
    pages = {"pages": [{"page": 1, "heading": "LIATE", "text": "Pick u by LIATE: logs before polynomials."}]}
    gemini.queue("generateContent", json_response(pages))
    uploaded = client.post(
        f"/teacher/courses/{C272}/materials",
        headers=prof_h,
        files={"file": ("Lecture 7.png", b"png-bytes", "image/png")},
        data={"kind": "slides"},
    )
    assert uploaded.status_code == 201
    material_id = uploaded.json()["material"]["id"]

    materials = client.get(f"/teacher/courses/{C272}", headers=prof_h).json()["materials"]
    assert next(m for m in materials if m["id"] == material_id)["status"] == "ready"
    [chunk] = client.app.state.container.repo.list_chunks(material_id)
    assert chunk.content == "Lecture 7, page 1 (LIATE). Pick u by LIATE: logs before polynomials."
    assert gemini.calls_to("batchEmbedContents")[0].body["requests"][0]["taskType"] == "RETRIEVAL_DOCUMENT"

    # Students' questions now find the new file.
    send(client, sam, PROBLEM_3, "How does LIATE pick u?")
    assert "Pick u by LIATE" in gemini.calls_to("generateContent")[-1].body["contents"][-1]["parts"][0]["text"]


def test_upload_fails_cleanly_when_gemini_is_down(client, prof_h, gemini):
    gemini.queue("generateContent", *[error_response(503)] * 10)
    material_id = client.post(
        f"/teacher/courses/{C272}/materials",
        headers=prof_h,
        files={"file": ("Notes.png", b"png", "image/png")},
        data={"kind": "notes"},
    ).json()["material"]["id"]
    material = next(m for m in client.get(f"/teacher/courses/{C272}", headers=prof_h).json()["materials"]
                    if m["id"] == material_id)
    assert material["status"] == "failed"
    assert "busy" in material["error"]
