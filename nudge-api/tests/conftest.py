import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

SAM = "samlee@andrew.cmu.edu"
ALEX = "alexchen@andrew.cmu.edu"
PROF_H = "profh@cmu.edu"
PROF_K = "profk@cmu.edu"


@pytest.fixture
def client() -> TestClient:
    """A fresh app with freshly seeded data for every test."""
    app = create_app(Settings(_env_file=None, mock_processing_seconds=0))
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
