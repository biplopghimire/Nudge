import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain import User
from app.integrations.auth import JWTAuthProvider
from app.main import create_app
from tests.conftest import PROF_H


def test_login_returns_role(client):
    response = client.post("/auth/login", json={"email": PROF_H, "password": "x"})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "teacher"


def test_unknown_email_is_rejected(client):
    response = client.post("/auth/login", json={"email": "nobody@cmu.edu", "password": "x"})
    assert response.status_code == 401
    assert response.json()["error"] == "invalid_login"


def test_missing_token_is_401(client):
    response = client.get("/student/me")
    assert response.status_code == 401
    assert set(response.json()) == {"error", "message"}


def test_bad_token_is_401(client):
    response = client.get("/student/me", headers={"Authorization": "Bearer nope"})
    assert response.status_code == 401


def test_student_token_on_teacher_endpoint_is_403(client, sam):
    assert client.get("/teacher/courses", headers=sam).status_code == 403


def test_teacher_token_on_student_endpoint_is_403(client, prof_h):
    assert client.get("/student/courses", headers=prof_h).status_code == 403


def test_validation_errors_use_error_shape(client, sam):
    response = client.post("/student/courses/join", headers=sam, json={})
    assert response.status_code == 422
    assert response.json()["error"] == "invalid_request"


# ---- sign-up and real login (NUDGE_AUTH=jwt) ----

SECRET = "test-secret-that-is-at-least-32-characters"
NEW_STUDENT = {
    "name": "Jordan Rivera",
    "email": "JRivera@andrew.cmu.edu",
    "password": "correct horse",
    "role": "student",
}


@pytest.fixture
def jwt_client() -> TestClient:
    return TestClient(create_app(Settings(_env_file=None, auth="jwt", jwt_secret=SECRET)))


def test_signup_then_login_with_real_passwords(jwt_client):
    created = jwt_client.post("/auth/signup", json=NEW_STUDENT)
    assert created.status_code == 201
    token = created.json()["token"]
    assert created.json()["user"]["email"] == "jrivera@andrew.cmu.edu"
    me = jwt_client.get("/student/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["user"]["name"] == "Jordan Rivera"

    good = jwt_client.post("/auth/login", json={"email": "jrivera@andrew.cmu.edu", "password": "correct horse"})
    assert good.status_code == 200
    bad = jwt_client.post("/auth/login", json={"email": "jrivera@andrew.cmu.edu", "password": "wrong horse"})
    assert bad.status_code == 401


def test_example_accounts_have_no_password_under_real_login(jwt_client):
    assert jwt_client.post("/auth/login", json={"email": PROF_H, "password": "anything"}).status_code == 401


def test_mock_tokens_are_rejected_under_real_login(jwt_client):
    fake = "mock-a0000000-0000-4000-8000-000000000001"
    assert jwt_client.get("/student/me", headers={"Authorization": f"Bearer {fake}"}).status_code == 401


def test_tampered_and_expired_tokens_are_rejected():
    provider = JWTAuthProvider(SECRET, token_days=-1)
    expired = provider.issue_token(User("u1", "A", "a@b.co", "student"))
    assert provider.user_id_from_token(expired) is None
    other = JWTAuthProvider("another-secret-that-is-also-32-characters!")
    fresh = other.issue_token(User("u1", "A", "a@b.co", "student"))
    assert JWTAuthProvider(SECRET).user_id_from_token(fresh) is None


def test_password_hashes_are_salted():
    provider = JWTAuthProvider(SECRET)
    first, second = provider.hash_password("same password"), provider.hash_password("same password")
    assert first != second
    assert provider.verify_password("same password", first)
    assert not provider.verify_password("same password", None)


@pytest.mark.parametrize(
    "change, error",
    [
        ({"name": " "}, "missing_name"),
        ({"email": "not-an-email"}, "invalid_email"),
        ({"password": "short"}, "weak_password"),
    ],
)
def test_signup_validation(client, change, error):
    response = client.post("/auth/signup", json={**NEW_STUDENT, **change})
    assert response.status_code == 400
    assert response.json()["error"] == error


def test_signup_with_taken_email(client):
    response = client.post("/auth/signup", json={**NEW_STUDENT, "email": "SamLee@andrew.cmu.edu"})
    assert response.status_code == 409
    assert response.json()["error"] == "email_taken"


def test_new_teacher_can_create_a_course(client):
    token = client.post("/auth/signup", json={**NEW_STUDENT, "email": "t@cmu.edu", "role": "teacher"}).json()["token"]
    course = client.post(
        "/teacher/courses",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "67-443", "section": "A", "semester": "Fall 2026"},
    )
    assert course.status_code == 201
