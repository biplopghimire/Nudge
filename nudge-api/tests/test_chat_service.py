"""ChatService on the seeded in-memory data with a scripted AI: retrieval, citations, settings, titles."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from app.domain import Message
from app.errors import ApiError
from app.integrations.ai import AIUnavailable, Reply
from app.repositories.memory import InMemoryRepository
from app.services.chat import ChatService, EarlierAttachment, merge_rankings
from tests.fakes import ScriptedAI
from tests.test_threads import C272, PROBLEM_3, PROF_H_THREAD, PS4_SOLUTIONS

NOW = datetime(2026, 11, 1, tzinfo=UTC)


@pytest.fixture
def repo():
    return InMemoryRepository()


def chat(repo, ai):
    return ChatService(repo, ai)


def answer(repo, ai, question="How do I use substitution on problem 3?", thread=PROBLEM_3, history=None, **kwargs):
    thread = repo.get_thread(thread)
    return chat(repo, ai).answer(thread, repo.get_course(thread.course_id), question, history or [], **kwargs)


def test_reply_text_comes_from_the_ai(repo):
    ai = ScriptedAI(Reply("What is u here?", [1]))
    result = answer(repo, ai)
    assert result.content == "What is u here?"
    assert len(result.citations) == 1


def test_sources_are_course_material_with_readable_titles(repo):
    ai = ScriptedAI()
    answer(repo, ai)
    sources = ai.requests[0].sources
    assert sources, "the seeded lecture and problem set are found"
    assert [s.number for s in sources] == list(range(1, len(sources) + 1))
    assert {"Lecture 6", "Problem Set 4"} <= {s.title for s in sources}


def test_citations_are_deduplicated_capped_and_never_restricted(repo):
    ai = ScriptedAI()  # says it used every source
    result = answer(repo, ai, attachment=b"work", attachment_mime="image/png")
    keys = [(c.title, c.page) for c in result.citations]
    assert len(keys) == len(set(keys))
    assert len(result.citations) <= 3
    assert all(c.material_id != PS4_SOLUTIONS for c in result.citations)


def test_no_citations_when_the_course_turns_them_off(repo):
    repo.update_course_settings(C272, {"cite_materials": False})
    assert answer(repo, ScriptedAI()).citations == []


def test_solution_keys_are_searched_only_with_student_work(repo):
    ai = ScriptedAI()
    answer(repo, ai)
    assert not any(s.restricted for s in ai.requests[-1].sources)

    answer(repo, ai, attachment=b"work", attachment_mime="image/png")
    assert any(s.restricted for s in ai.requests[-1].sources)


def test_earlier_photo_also_unlocks_solution_keys(repo):
    ai = ScriptedAI()
    history = [Message("m1", PROBLEM_3, "student", "", NOW, attachment_type="image")]
    answer(repo, ai, "Is this right?", history=history,
           earlier_attachment=EarlierAttachment("m1", b"img", "image/jpeg"))
    request = ai.requests[0]
    assert any(s.restricted for s in request.sources)
    assert request.history[0].attachment == b"img"
    assert request.history[0].text == "[sent a photo]"


def test_solution_keys_stay_out_when_the_course_says_so(repo):
    repo.update_course_settings(C272, {"use_solution_keys": False})
    ai = ScriptedAI()
    answer(repo, ai, attachment=b"work", attachment_mime="image/png")
    assert not any(s.restricted for s in ai.requests[0].sources)


def test_assignment_text_is_sent_for_assignment_chats(repo):
    ai = ScriptedAI()
    answer(repo, ai)
    assert "x cos(x^2)" in ai.requests[0].assignment_text


def test_teachers_get_full_answers_even_with_hints_only(repo):
    assert repo.get_course(C272).settings.hints_only
    ai = ScriptedAI()
    answer(repo, ai, "What mistakes should I watch for?", thread=PROF_H_THREAD)
    request = ai.requests[0]
    assert request.asker_role == "teacher"
    assert request.settings.hints_only is False
    assert repo.get_course(C272).settings.hints_only, "the course's own setting is unchanged"


def test_ai_outage_becomes_a_503(repo):
    with pytest.raises(ApiError) as caught:
        answer(repo, ScriptedAI(AIUnavailable("down")))
    assert (caught.value.status, caught.value.error) == (503, "nudge_busy")


def test_unknown_material_gets_a_generic_title(repo):
    chunk = next(iter(repo.chunks.values()))
    orphan = replace(chunk, id="orphan", material_id="gone")
    [source] = chat(repo, ScriptedAI())._sources([orphan])
    assert source.title == "Course material"


def test_search_context_uses_the_last_few_messages_and_trims_replies():
    history = [
        Message("1", "t", "student", "first", NOW),
        Message("2", "t", "student", "second", NOW),
        Message("3", "t", "student", "", NOW),  # photo only: skipped
        Message("4", "t", "nudge", "x" * 1000, NOW),
        Message("5", "t", "student", "latest", NOW),
    ]
    context = ChatService._search_context(history)
    assert context.split("\n") == ["second", "x" * 300, "latest"]


def test_blank_question_still_searches(repo):
    assert chat(repo, ScriptedAI()).retrieve(C272, "   ", include_restricted=False)


def test_merge_keeps_the_best_and_respects_the_limit():
    from app.domain import Chunk

    a, b, c = (Chunk(x, "c", "m", x) for x in "abc")
    assert [ch.id for ch in merge_rankings([a, b, c], [b], keep=2)] == ["b", "a"]
    assert merge_rankings([], []) == []


# ---- chat titles ----

@pytest.mark.parametrize("ai_title, question, expected", [
    ('"Integration by parts."', "anything", "Integration by parts"),
    ("**PS 4   problem 3**", "anything", "PS 4 problem 3"),
    ("x" * 61, "How do I choose u for integration by parts?", "How do I choose u for"),
    (AIUnavailable("down"), "When is the midterm exam this semester?", "When is the midterm exam this"),
    (AIUnavailable("down"), "", None),
    ("", "", None),
])
def test_title_for(ai_title, question, expected, repo):
    assert chat(repo, ScriptedAI(title=ai_title)).title_for(question) == expected
