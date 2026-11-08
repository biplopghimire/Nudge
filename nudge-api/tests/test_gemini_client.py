"""GeminiClient against a fake Gemini (tests/fakes.py): request shapes, parsing and retries."""

import json

import httpx
import pytest

from app.domain import CourseSettings
from app.integrations.ai import (
    HINTS_ONLY_RULE,
    HISTORY_TURNS,
    RESTRICTED_RULE,
    TEACHER_RULE,
    AIUnavailable,
    ReplyRequest,
    Source,
    Turn,
)
from app.integrations.gemini import EMBED_BATCH, GeminiError, _retry_delay, _text_of
from tests.fakes import FakeGemini, embeddings_for, error_response, json_response, text_response


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr("app.integrations.gemini.time.sleep", lambda _: None)


def ask(question="How do I pick u?", sources=None, **kwargs) -> ReplyRequest:
    return ReplyRequest(question=question, settings=kwargs.pop("settings", CourseSettings()),
                        sources=sources or [], **kwargs)


LECTURE = Source(1, "Lecture 7", 2, "LIATE: pick u as the log, inverse trig, algebraic...")
KEY = Source(2, "PS 4 Solutions", 1, "u = x^2, answer (1/2) sin(x^2) + C", restricted=True)


# ---- response parsing ----

@pytest.mark.parametrize("details, expected", [
    ([{"retryDelay": "47s"}], 47.0),
    ([{"@type": "QuotaFailure"}, {"retryDelay": "1.5s"}], 1.5),
    ([{"retryDelay": "soon"}], None),
    ([], None),
    (None, None),
])
def test_retry_delay_is_read_from_error_details(details, expected):
    assert _retry_delay({"details": details}) == expected


def test_thinking_parts_are_left_out_of_the_text():
    response = {"candidates": [{"content": {"parts": [
        {"text": "Let me think...", "thought": True},
        {"text": "Use "}, {"text": "LIATE."},
    ]}}]}
    assert _text_of(response) == "Use LIATE."


def test_empty_answer_says_why():
    with pytest.raises(GeminiError, match="SAFETY"):
        _text_of({"candidates": [{"content": {"parts": []}, "finishReason": "SAFETY"}]})
    with pytest.raises(GeminiError, match="none"):
        _text_of({})


def test_reply_that_is_not_json_is_still_shown():
    fake = FakeGemini().queue("generateContent", text_response("Plain text, not JSON."))
    reply = fake.client().generate_reply(ask(sources=[LECTURE]))
    assert reply.text == "Plain text, not JSON."
    assert reply.used_sources == []


def test_only_real_unrestricted_source_numbers_are_kept():
    fake = FakeGemini().queue("generateContent", json_response({"reply": "See lecture 7.", "sources": [1, 2, 9]}))
    reply = fake.client().generate_reply(ask(sources=[LECTURE, KEY]))
    assert reply.used_sources == [1]


def test_empty_reply_field_falls_back_to_raw_text():
    raw = {"reply": "  ", "sources": []}
    reply = FakeGemini().queue("generateContent", json_response(raw)).client().generate_reply(ask())
    assert reply.text == json.dumps(raw)


# ---- what is sent ----

def test_key_and_model_are_in_the_request():
    fake = FakeGemini()
    fake.client(chat_models=["gemini-x"]).generate_reply(ask())
    call = fake.calls[0]
    assert call.model == "gemini-x" and call.method == "generateContent"
    assert call.headers["x-goog-api-key"] == "test-key"
    assert call.body["generationConfig"]["responseMimeType"] == "application/json"


def test_prompt_has_sources_assignment_and_question():
    fake = FakeGemini()
    fake.client().generate_reply(ask("Is step 2 right?", [LECTURE], assignment_text="PS 4 problem 3: x cos(x^2)"))
    prompt = fake.calls[0].body["contents"][-1]["parts"][0]["text"]
    assert "[1] Lecture 7, page 2" in prompt
    assert "CURRENT ASSIGNMENT" in prompt and "x cos(x^2)" in prompt
    assert prompt.endswith("QUESTION:\nIs step 2 right?")


def test_photo_only_question_gets_a_default_question_and_the_photo():
    fake = FakeGemini()
    fake.client().generate_reply(ask("", attachment=b"jpeg", attachment_mime="image/jpeg"))
    parts = fake.calls[0].body["contents"][-1]["parts"]
    assert "Can you check it?" in parts[0]["text"]
    assert parts[1]["inline_data"] == {"mime_type": "image/jpeg", "data": "anBlZw=="}


@pytest.mark.parametrize("kwargs, present, absent", [
    ({}, [HINTS_ONLY_RULE], [TEACHER_RULE, RESTRICTED_RULE]),
    ({"asker_role": "teacher"}, [TEACHER_RULE], [HINTS_ONLY_RULE]),
    ({"settings": CourseSettings(hints_only=False)}, ["explain answers fully"], [HINTS_ONLY_RULE]),
    ({"sources": [LECTURE, KEY]}, [RESTRICTED_RULE, "[2] RESTRICTED"], []),
])
def test_system_instruction_follows_the_request(kwargs, present, absent):
    fake = FakeGemini()
    fake.client().generate_reply(ask(**kwargs))
    sent = json.dumps(fake.calls[0].body)
    for text in present:
        assert json.dumps(text)[1:-1] in sent
    for text in absent:
        assert json.dumps(text)[1:-1] not in sent


def test_history_is_capped_and_blank_turns_dropped():
    history = [Turn("student" if i % 2 else "nudge", f"message {i}") for i in range(HISTORY_TURNS + 5)]
    history[-1] = Turn("student", "   ")  # blank, no attachment: dropped
    fake = FakeGemini()
    fake.client().generate_reply(ask(history=history))
    contents = fake.calls[0].body["contents"]
    assert len(contents) == HISTORY_TURNS - 1 + 1  # kept turns + the question
    assert contents[0]["parts"][0]["text"] == f"message {5}"
    assert {c["role"] for c in contents} == {"user", "model"}


# ---- retries and fallback ----

def test_timeout_moves_to_the_next_model():
    def slow(request):
        raise httpx.ReadTimeout("slow", request=request)

    fake = FakeGemini().queue("generateContent", slow)
    reply = fake.client(chat_models=["slow", "fast"]).generate_reply(ask(sources=[LECTURE]))
    assert reply.text == "Fake Gemini reply."
    assert [c.model for c in fake.calls] == ["slow", "fast"]


def test_second_pass_after_every_model_is_busy(monkeypatch):
    waits = []
    monkeypatch.setattr("app.integrations.gemini.time.sleep", waits.append)
    fake = FakeGemini().queue("generateContent", error_response(503), error_response(500))
    reply = fake.client(chat_models=["a", "b"]).generate_reply(ask(sources=[LECTURE]))
    assert reply.text == "Fake Gemini reply."
    assert [c.model for c in fake.calls] == ["a", "b", "a"]
    assert waits == [2.0]


def test_gives_up_after_every_pass():
    fake = FakeGemini().queue("generateContent", *[error_response(503, "high demand")] * 10)
    with pytest.raises(AIUnavailable, match="high demand"):
        fake.client(chat_models=["a", "b"], passes=2).generate_reply(ask())
    assert len(fake.calls) == 4


def test_rate_limit_error_carries_the_wait():
    fake = FakeGemini().queue("generateContent", error_response(429, "quota", retry_delay="30s"))
    with pytest.raises(GeminiError) as caught:
        fake.client()._post_once("m", "generateContent", {}, 1.0)
    assert caught.value.rate_limited and caught.value.retry_after == 30.0 and caught.value.retryable


def test_non_json_error_body_is_reported():
    fake = FakeGemini().queue("generateContent", httpx.Response(400, text="<html>Bad Request</html>"))
    with pytest.raises(GeminiError, match="Bad Request") as caught:
        fake.client(chat_models=["a", "b"]).generate_reply(ask())
    assert not caught.value.retryable
    assert len(fake.calls) == 1


# ---- titles ----

def test_title_stops_on_a_bad_request():
    fake = FakeGemini().queue("generateContent", error_response(400, "bad key"))
    with pytest.raises(AIUnavailable):
        fake.client(chat_models=["a", "b"]).generate_title("How do I pick u?")
    assert len(fake.calls) == 1


def test_title_for_a_photo_sends_the_photo():
    fake = FakeGemini().queue("generateContent", text_response("PS 4 problem 3"))
    title = fake.client().generate_title("", b"img", "image/png")
    assert title == "PS 4 problem 3"
    parts = fake.calls[0].body["contents"][0]["parts"]
    assert parts[0]["text"] == "(No text, only the attachment.)"
    assert parts[1]["inline_data"]["mime_type"] == "image/png"


# ---- transcription and embeddings ----

def test_photo_is_transcribed_in_one_call():
    pages = {"pages": [{"page": 7, "heading": "", "text": "  x^2 + 1  "}]}
    fake = FakeGemini().queue("generateContent", json_response(pages))
    progress = []
    result = fake.client().transcribe(b"img", "image/jpeg", on_progress=lambda d, t: progress.append((d, t)))
    assert len(result) == 1
    assert (result[0].page, result[0].heading, result[0].text) == (1, None, "x^2 + 1")
    assert progress == [(1, 1)]
    assert fake.calls[0].body["generationConfig"]["temperature"] == 0


def test_embeddings_are_sent_in_batches_with_the_task_type():
    fake = FakeGemini()
    vectors = fake.client().embed([f"chunk {i}" for i in range(EMBED_BATCH * 2 + 3)], task="document")
    assert len(vectors) == EMBED_BATCH * 2 + 3
    batches = fake.calls_to("batchEmbedContents")
    assert [len(c.body["requests"]) for c in batches] == [EMBED_BATCH, EMBED_BATCH, 3]
    assert {r["taskType"] for r in batches[0].body["requests"]} == {"RETRIEVAL_DOCUMENT"}

    fake.client().embed(["question"], task="query")
    assert fake.calls[-1].body["requests"][0]["taskType"] == "RETRIEVAL_QUERY"


def test_empty_text_is_embedded_as_a_space():
    fake = FakeGemini()
    fake.client().embed([""])
    assert fake.calls[0].body["requests"][0]["content"]["parts"][0]["text"] == " "


def test_embeddings_are_normalized():
    fake = FakeGemini().queue("batchEmbedContents", lambda r: embeddings_for(r, value=5.0))
    [vector] = fake.client().embed(["x"])
    assert vector[0] == pytest.approx(1.0)
