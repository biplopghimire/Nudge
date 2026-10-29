"""The Nudge engine pieces: Gemini client, ingestion, retrieval and citations."""

import json
from pathlib import Path

import httpx
import pytest

from app.domain import Chunk, CourseSettings, Material
from app.integrations.ai import (
    AIUnavailable,
    MockAIClient,
    ReplyRequest,
    Source,
    build_instructions,
    format_sources,
)
from app.integrations.gemini import GeminiClient, split_pdf
from app.integrations.storage import LocalStorage
from app.repositories.memory import InMemoryRepository
from app.services.chat import merge_rankings
from app.services.common import citation_title
from app.services.ingestion import IngestionService, split_into_chunks
from tests.test_threads import C272, PROBLEM_3, send

LECTURE = Path(__file__).resolve().parent.parent / "samples" / "lecture-7-integration-by-parts.pdf"


# ---- a fake Gemini ----

def reply_body(payload: dict) -> dict:
    return {"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}, "finishReason": "STOP"}]}


def fake_gemini(handler, **kwargs) -> GeminiClient:
    return GeminiClient("test-key", transport=httpx.MockTransport(handler), **kwargs)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda _: None)


def request_for(sources: list[Source], **kwargs) -> ReplyRequest:
    return ReplyRequest(question="How do I pick u?", settings=CourseSettings(), sources=sources, **kwargs)


def test_busy_model_falls_back_to_the_next():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        model = request.url.path.split("/models/")[1].split(":")[0]
        calls.append(model)
        if model == "busy":
            return httpx.Response(503, json={"error": {"message": "high demand"}})
        return httpx.Response(200, json=reply_body({"reply": "Try LIATE.", "sources": [1]}))

    client = fake_gemini(handler, chat_models=["busy", "backup"])
    reply = client.generate_reply(request_for([Source(1, "Lecture 7", 2, "LIATE rule")]))
    assert reply.text == "Try LIATE."
    assert reply.used_sources == [1]
    assert calls == ["busy", "backup"]


def test_all_models_down_raises_ai_unavailable():
    client = fake_gemini(lambda r: httpx.Response(503, json={"error": {"message": "busy"}}), chat_models=["a", "b"])
    with pytest.raises(AIUnavailable):
        client.generate_reply(request_for([]))


def test_bad_request_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(400, json={"error": {"message": "bad key"}})

    with pytest.raises(AIUnavailable):
        fake_gemini(handler, chat_models=["a", "b"]).generate_reply(request_for([]))
    assert len(calls) == 1


def test_restricted_sources_are_never_reported_as_used():
    handler = lambda r: httpx.Response(200, json=reply_body({"reply": "Check your last line.", "sources": [1, 2, 9]}))  # noqa: E731
    sources = [Source(1, "PS 4 Solutions", 1, "answer", restricted=True), Source(2, "Lecture 6", 4, "u-sub")]
    reply = fake_gemini(handler, chat_models=["m"]).generate_reply(request_for(sources))
    assert reply.used_sources == [2]


def test_embeddings_are_batched_and_unit_length():
    sizes = []

    def handler(request):
        batch = json.loads(request.content)["requests"]
        sizes.append(len(batch))
        assert batch[0]["outputDimensionality"] == 768
        return httpx.Response(200, json={"embeddings": [{"values": [3.0, 4.0] + [0.0] * 766} for _ in batch]})

    vectors = fake_gemini(handler, chat_models=["m"]).embed(["text"] * 150, task="query")
    assert sizes == [50, 50, 50]
    assert len(vectors) == 150 and len(vectors[0]) == 768
    assert vectors[0][:2] == pytest.approx([0.6, 0.8])


def test_transcription_numbers_pages_across_parts():
    def handler(request):
        prompt = json.loads(request.content)["contents"][0]["parts"][1]["text"]
        first = int(prompt.rsplit("numbered from ", 1)[1].split(",")[0])
        return httpx.Response(200, json=reply_body({"pages": [{"page": first, "text": f"page {first}"}]}))

    client = fake_gemini(handler, chat_models=["m"])
    pages = client.transcribe(b"%PDF fake", "image/jpeg")
    assert [(p.page, p.text) for p in pages] == [(1, "page 1")]


def test_split_pdf_keeps_every_page():
    parts = split_pdf(LECTURE.read_bytes(), pages_per_part=3)
    assert [first for first, _ in parts] == [1, 4]


# ---- instructions ----

def test_instructions_follow_settings():
    hints = build_instructions(request_for([]))
    assert "HINTS ONLY" in hints
    full = build_instructions(ReplyRequest(question="q", settings=CourseSettings(hints_only=False), sources=[]))
    assert "HINTS ONLY" not in full
    teacher = build_instructions(request_for([], asker_role="teacher"))
    assert "HINTS ONLY" not in teacher and "teacher" in teacher
    restricted = build_instructions(request_for([Source(1, "Key", 1, "x", restricted=True)]))
    assert "solution keys" in restricted


def test_sources_are_numbered_and_tagged():
    text = format_sources([Source(1, "Lecture 7", 2, "LIATE"), Source(2, "PS 4 Solutions", 1, "x", restricted=True)])
    assert "[1] Lecture 7, page 2\nLIATE" in text
    assert "[2] RESTRICTED PS 4 Solutions, page 1" in text


# ---- ingestion ----

def test_chunks_are_capped_at_400_words():
    pieces = split_into_chunks("word " * 900 + "\n\nshort section")
    assert [len(p.split()) for p in pieces] == [400, 400, 100, 2]


def test_ingesting_a_real_pdf(tmp_path):
    repo = InMemoryRepository()
    storage = LocalStorage(str(tmp_path), "bucket")
    storage.upload("courses/x/lecture7.pdf", LECTURE.read_bytes(), "application/pdf")
    material = repo.create_material(
        Material("m7", C272, "lecture-7-integration-by-parts.pdf", "slides", 1, "courses/x/lecture7.pdf")
    )
    IngestionService(repo, MockAIClient(), storage).process_material(material.id)

    assert repo.get_material("m7").status == "ready"
    chunks = repo.list_chunks("m7")
    assert [c.page for c in chunks] == [1, 2, 3, 4]
    assert chunks[1].content.startswith("Lecture 7, page 2. ")
    assert "LIATE" in chunks[1].content
    assert all(len(c.embedding) == 768 for c in chunks)


def test_missing_file_marks_material_failed(tmp_path):
    repo = InMemoryRepository()
    material = repo.create_material(Material("m8", C272, "Gone.pdf", "notes", 1, "nowhere.pdf"))
    IngestionService(repo, MockAIClient(), LocalStorage(str(tmp_path), "b")).process_material(material.id)
    assert repo.get_material("m8").status == "failed"


def test_local_storage_rejects_paths_outside_its_folder(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(str(tmp_path), "b").upload("../escape.txt", b"x", None)


# ---- retrieval and citations ----

def test_merge_prefers_chunks_found_both_ways():
    a, b, c = (Chunk(i, C272, "m", i) for i in "abc")
    assert [x.id for x in merge_rankings([a, b], [b, c])][0] == "b"


def test_citation_titles():
    assert citation_title("Lecture 6 - Substitution.pdf") == "Lecture 6"
    assert citation_title("lecture-7-integration-by-parts.pdf") == "Lecture 7"
    assert citation_title("Problem_Set_4.pdf") == "Problem Set 4"
    assert citation_title("Syllabus.pdf") == "Syllabus"


def test_ai_outage_returns_503_and_saves_nothing(client, sam, monkeypatch):
    def down(*args, **kwargs):
        raise AIUnavailable("down")

    monkeypatch.setattr(client.app.state.container.ai, "generate_reply", down)
    before = len(client.get(f"/threads/{PROBLEM_3}", headers=sam).json()["messages"])
    response = send(client, sam, PROBLEM_3, "Is this right?")
    assert response.status_code == 503
    assert response.json()["error"] == "nudge_busy"
    assert len(client.get(f"/threads/{PROBLEM_3}", headers=sam).json()["messages"]) == before


def test_upload_embeddings_wait_out_the_rate_limit(monkeypatch):
    waits = []
    monkeypatch.setattr("app.integrations.gemini.time.sleep", waits.append)
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": {"message": "quota", "details": [{"retryDelay": "12s"}]}})
        batch = json.loads(request.content)["requests"]
        return httpx.Response(200, json={"embeddings": [{"values": [1.0] + [0.0] * 767} for _ in batch]})

    vectors = fake_gemini(handler, chat_models=["m"]).embed(["a", "b"], task="document")
    assert len(vectors) == 2
    assert waits == [12.0]


def test_question_embeddings_do_not_wait_long():
    handler = lambda r: httpx.Response(429, json={"error": {"message": "quota"}})  # noqa: E731
    with pytest.raises(AIUnavailable):
        fake_gemini(handler, chat_models=["m"]).embed(["question"], task="query")


class RateLimitedAI(MockAIClient):
    def embed(self, texts, task="document"):
        error = AIUnavailable("quota")
        error.rate_limited = True
        raise error


def test_failed_file_records_a_reason_and_progress(tmp_path):
    repo = InMemoryRepository()
    storage = LocalStorage(str(tmp_path), "bucket")
    storage.upload("courses/x/l7.pdf", LECTURE.read_bytes(), "application/pdf")
    repo.create_material(Material("m9", C272, "Lecture 7.pdf", "slides", 1, "courses/x/l7.pdf"))
    repo.start_processing("m9")
    IngestionService(repo, RateLimitedAI(), storage).process_material("m9")

    material = repo.get_material("m9")
    assert material.status == "failed"
    assert "usage limit" in material.error
    assert material.progress >= 75  # it got through reading the pages first


def test_missing_text_reason(tmp_path):
    repo = InMemoryRepository()
    repo.create_material(Material("m10", C272, "Gone.pdf", "notes", 1, "nowhere.pdf"))
    IngestionService(repo, MockAIClient(), LocalStorage(str(tmp_path), "b")).process_material("m10")
    assert repo.get_material("m10").error == "The uploaded file couldn't be found. Upload it again."


def test_teacher_can_retry_a_failed_file(client, prof_h):
    lecture = "d0000000-0006-4000-8000-000000000001"
    repo = client.app.state.container.repo
    repo.set_material_status(lecture, "failed", "The AI service was busy while reading this file.")

    detail = client.get(f"/teacher/courses/{C272}", headers=prof_h).json()
    failed = next(m for m in detail["materials"] if m["id"] == lecture)
    assert failed["status"] == "failed" and "busy" in failed["error"]

    retried = client.post(f"/teacher/materials/{lecture}/retry", headers=prof_h)
    assert retried.status_code == 200
    assert retried.json()["material"]["status"] == "processing"
    assert retried.json()["material"]["error"] is None


def test_students_cannot_retry(client, sam):
    lecture = "d0000000-0006-4000-8000-000000000001"
    assert client.post(f"/teacher/materials/{lecture}/retry", headers=sam).status_code == 403
