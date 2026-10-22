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
