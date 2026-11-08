"""Every endpoint returns the same shape as its example JSON in nudge-api/.

If someone changes a response or an example file, this test says which keys
no longer match.
"""

import json
from pathlib import Path

import pytest

from tests.conftest import ALEX, PROF_H, SAM, login

EXAMPLES_DIR = Path(__file__).resolve().parent.parent
EXAMPLES = sorted(
    path for folder in ("shared", "student", "teacher") for path in (EXAMPLES_DIR / folder).glob("*.json")
)

# Sam is already in K7M4QX, so join a course Alex is not in yet.
JOIN_OVERRIDE = {"joinCode": "H2QW9D"}


def assert_same_shape(expected, actual, where="body"):
    if isinstance(expected, dict):
        assert isinstance(actual, dict), f"{where}: expected an object, got {actual!r}"
        assert set(actual) == set(expected), (
            f"{where}: missing {sorted(set(expected) - set(actual))}, "
            f"extra {sorted(set(actual) - set(expected))}"
        )
        for key in expected:
            if expected[key] is not None and actual[key] is not None:
                assert_same_shape(expected[key], actual[key], f"{where}.{key}")
    elif isinstance(expected, list):
        assert isinstance(actual, list), f"{where}: expected a list"
        if expected and actual:
            assert_same_shape(expected[0], actual[0], f"{where}[0]")


def call_example(client, example: dict):
    path = example["path"]
    request = example["request"]
    for name, value in (request.get("params") or {}).items():
        path = path.replace("{" + name + "}", value)

    if path == "/auth/signup":
        return client.post(path, json={**request["body"], "password": "long enough"})
    if path.startswith("/auth"):
        return client.post(path, json={"email": SAM, "password": "x"})

    if path.startswith("/teacher"):
        headers = login(client, PROF_H)
    elif path == "/student/courses/join":
        headers = login(client, ALEX)
    else:
        headers = login(client, SAM)

    method = example["method"]
    if path.endswith("/materials") and method == "POST":
        return client.post(
            path,
            headers=headers,
            files={"file": ("Lecture 6 - Substitution.pdf", b"%PDF-1.4 mock", "application/pdf")},
            data={"kind": "slides", "restricted": "false"},
        )
    if path.endswith("/messages") and method == "POST":
        return client.post(
            path,
            headers=headers,
            data={"content": "", "attachmentSource": "camera"},
            files={"attachment": ("work.jpg", b"jpeg", "image/jpeg")},
        )
    if method == "GET":
        return client.get(path, headers=headers)

    body = JOIN_OVERRIDE if path == "/student/courses/join" else request.get("body")
    return client.request(method, path, headers=headers, json=body)


@pytest.mark.parametrize("example_path", EXAMPLES, ids=lambda p: f"{p.parent.name}/{p.name}")
def test_matches_example(client, example_path):
    example = json.loads(example_path.read_text())
    if "planned" in example:
        pytest.skip(f"planned: {example['planned']}")
    response = call_example(client, example)
    assert response.status_code == example["response"]["status"], response.text
    assert_same_shape(example["response"]["body"], response.json())
