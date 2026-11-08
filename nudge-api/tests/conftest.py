"""Every API test runs against the in-memory repository, and also against
Postgres when NUDGE_TEST_DATABASE_URL is set, for example:

    createdb nudge_test
    NUDGE_DATABASE_URL=postgresql:///nudge_test python -m scripts.db reset
    NUDGE_TEST_DATABASE_URL=postgresql:///nudge_test pytest

Tests never reach Gemini (or any other real service). Before the app is
imported, the NUDGE_* switches are forced to their mocks, so neither the shell
nor nudge-api/.env (which may say NUDGE_AI=gemini) can switch them, and any
real HTTP request made through httpx fails the test. Tests that exercise
GeminiClient give it a fake transport (see tests/fakes.py).
"""

import copy
import os

# Must run before anything imports app.main, which builds an app from the environment at import time.
for _name in [n for n in os.environ if n.startswith("NUDGE_") and n != "NUDGE_TEST_DATABASE_URL"]:
    del os.environ[_name]
os.environ.update(NUDGE_REPOSITORY="memory", NUDGE_AI="mock", NUDGE_STORAGE="mock", NUDGE_AUTH="mock")
os.environ["NUDGE_GEMINI_API_KEY"] = ""  # overrides a real key in .env

import httpx  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import Settings  # noqa: E402
from app.integrations.ai import MockAIClient  # noqa: E402
from app.main import create_app  # noqa: E402
from app.repositories.seed import default_seed  # noqa: E402


class RealNetworkBlocked(RuntimeError):
    """A test tried to make a real HTTP request (for example to Gemini)."""


@pytest.fixture(autouse=True)
def block_real_http(monkeypatch):
    """httpx's real transport refuses every request. httpx.MockTransport and
    FastAPI's TestClient use their own transports, so they still work."""

    def refuse(self, request: httpx.Request):
        raise RealNetworkBlocked(f"Tests must not make real HTTP requests: {request.method} {request.url}")

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", refuse)

SAM = "samlee@andrew.cmu.edu"
ALEX = "alexchen@andrew.cmu.edu"
PROF_H = "profh@cmu.edu"
PROF_K = "profk@cmu.edu"

TEST_DATABASE_URL = os.environ.get("NUDGE_TEST_DATABASE_URL")
BACKENDS = ["memory"] + (["postgres"] if TEST_DATABASE_URL else [])


@pytest.fixture(scope="session")
def postgres_repo():
    from app.repositories.postgres import PostgresRepository

    repo = PostgresRepository(TEST_DATABASE_URL, max_size=4)
    yield repo
    repo.close()


@pytest.fixture(params=BACKENDS)
def client(request) -> TestClient:
    """A fresh app with freshly seeded data for every test."""
    app = create_app(Settings(_env_file=None, mock_processing_seconds=0))
    if request.param == "postgres":
        from app.repositories.pg_seed import clear, insert_seed

        repo = request.getfixturevalue("postgres_repo")
        clear(repo)
        insert_seed(repo, copy.deepcopy(default_seed()), MockAIClient().embed)
        app.state.container.repo = repo
    return TestClient(app)


def login(client: TestClient, email: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"email": email, "password": "anything"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


@pytest.fixture
def sam(client):
    return login(client, SAM)


@pytest.fixture
def alex(client):
    return login(client, ALEX)


@pytest.fixture
def prof_h(client):
    return login(client, PROF_H)


@pytest.fixture
def prof_k(client):
    return login(client, PROF_K)
