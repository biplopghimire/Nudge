"""End-to-end check of the Nudge engine against a running server.

    python -m scripts.smoke                         # http://localhost:8000
    python -m scripts.smoke https://your-deploy.example.com

As Prof. H: upload samples/lecture-7-integration-by-parts.pdf to 67-272 and wait
until it is processed. As Sam: ask about it, try to get the answer, ask something
the course does not cover, and send a photo of work. Prints each reply and its
citation chips so you can judge the answers.
"""

import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
LECTURE = ROOT / "samples" / "lecture-7-integration-by-parts.pdf"
PHOTO = ROOT.parent / "api-tests" / "samples" / "handwritten-work.jpg"
COURSE = "c0000000-0272-4000-8000-000000000001"  # 67-272 Sec 1 from the seed


def login(http: httpx.Client, email: str) -> dict[str, str]:
    response = http.post("/auth/login", json={"email": email, "password": "demo"})
    response.raise_for_status()
    return {"Authorization": f"Bearer {response.json()['token']}"}


def show(label: str, response: httpx.Response) -> None:
    if response.status_code >= 400:
        print(f"\n[{label}] HTTP {response.status_code}: {response.text[:300]}")
        return
    body = response.json()
    reply = body["reply"]
    chips = ", ".join(f"{c['title']} p.{c['page']}" for c in reply["citations"]) or "none"
    print(f"\n[{label}]\nStudent: {body['sentMessage']['content'] or '(photo)'}")
    print(f"Nudge:   {reply['content']}\nChips:   {chips}")


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    with httpx.Client(base_url=base, timeout=300) as http:
        teacher = login(http, "profh@cmu.edu")
        print(f"Uploading {LECTURE.name} ...")
        started = time.monotonic()
        upload = http.post(
            f"/teacher/courses/{COURSE}/materials",
            headers=teacher,
            files={"file": (LECTURE.name, LECTURE.read_bytes(), "application/pdf")},
            data={"kind": "slides"},
        )
        upload.raise_for_status()
        material = upload.json()["material"]
        while True:
            materials = http.get(f"/teacher/courses/{COURSE}", headers=teacher).json()["materials"]
            status = next(m["status"] for m in materials if m["id"] == material["id"])
            if status != "processing":
                break
            time.sleep(2)
        print(f"Material {status} after {time.monotonic() - started:.0f}s")
        if status != "ready":
            sys.exit(1)

        student = login(http, "samlee@andrew.cmu.edu")
        thread = http.post("/threads", headers=student, json={"courseId": COURSE, "title": "Lecture 7"}).json()
        thread_id = thread["thread"]["id"]

        def ask(label: str, text: str = "", photo: Path | None = None) -> None:
            files = {"attachment": (photo.name, photo.read_bytes(), "image/jpeg")} if photo else None
            data = {"content": text, **({"attachmentSource": "camera"} if photo else {})}
            started = time.monotonic()
            response = http.post(f"/threads/{thread_id}/messages", headers=student, data=data, files=files)
            show(f"{label}, {time.monotonic() - started:.1f}s", response)

        ask("Concept question", "How do I decide which part is u in integration by parts?")
        ask("Asks for the answer", "Just tell me the final answer to the integral of x cos x dx.")
        ask("Not in the course", "What's the best way to train a neural network?")
        if PHOTO.exists():
            ask("Photo of work (PS 4 problem 3)", "Is this right?", PHOTO)


if __name__ == "__main__":
    main()
