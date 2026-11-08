"""The test suite itself: it runs on mocks and cannot reach Gemini."""

import pytest

import app.main
from app.config import Settings
from app.deps import build_ai
from app.domain import CourseSettings
from app.integrations.ai import MockAIClient, ReplyRequest
from app.integrations.gemini import GeminiClient
from app.integrations.storage import MockStorage
from app.repositories.memory import InMemoryRepository
from tests.conftest import RealNetworkBlocked


def test_the_imported_app_uses_mocks_even_if_env_says_gemini():
    container = app.main.app.state.container
    assert isinstance(container.ai, MockAIClient)
    assert isinstance(container.repo, InMemoryRepository)
    assert isinstance(container.storage, MockStorage)


def test_test_client_uses_mock_ai(client):
    container = client.app.state.container
    assert isinstance(container.ai, MockAIClient)
    assert container.settings.ai == "mock"


def test_a_real_gemini_request_is_blocked():
    gemini = GeminiClient("not-a-real-key", chat_models=["gemini-3.5-flash"])  # no fake transport
    with pytest.raises(RealNetworkBlocked):
        gemini.generate_reply(ReplyRequest(question="hi", settings=CourseSettings(), sources=[]))


def test_gemini_needs_a_key():
    with pytest.raises(RuntimeError, match="NUDGE_GEMINI_API_KEY"):
        build_ai(Settings(_env_file=None, ai="gemini", gemini_api_key=None))


def test_building_gemini_makes_no_requests():
    ai = build_ai(Settings(_env_file=None, ai="gemini", gemini_api_key="k", gemini_chat_models=["a", "b"]))
    assert isinstance(ai, GeminiClient)
    assert ai.chat_models == ["a", "b"]
