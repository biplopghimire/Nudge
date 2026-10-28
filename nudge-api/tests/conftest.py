"""Every API test runs against the in-memory repository, and also against
Postgres when NUDGE_TEST_DATABASE_URL is set, for example:

    createdb nudge_test
    NUDGE_DATABASE_URL=postgresql:///nudge_test python -m scripts.db reset
    NUDGE_TEST_DATABASE_URL=postgresql:///nudge_test pytest
"""

import copy
import os

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.integrations.ai import MockAIClient
from app.main import create_app
from app.repositories.seed import default_seed

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
