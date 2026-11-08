"""IngestionService with scripted transcriptions: chunk labels, progress, retries and failure reasons."""

import pytest

from app.domain import Material
from app.integrations.ai import EMBEDDING_SIZE, AIUnavailable, TranscribedPage
from app.integrations.storage import MockStorage
from app.repositories.memory import InMemoryRepository
from app.services.ingestion import EMBED_STEP, FileUnreadable, IngestionService, failure_reason, guess_mime
from tests.fakes import ScriptedAI
from tests.test_threads import C272

PAGES = [
    TranscribedPage(1, "Integration by parts.\n\n$\\int u\\,dv = uv - \\int v\\,du$", heading="Slide 1"),
    TranscribedPage(2, "Choose u with LIATE."),
]


class RecordingRepo(InMemoryRepository):
    def __init__(self):
        super().__init__()
        self.progress: list[tuple[int, str]] = []

    def set_material_progress(self, material_id, progress, stage):
        self.progress.append((progress, stage))
        super().set_material_progress(material_id, progress, stage)


def setup(pages, title="Lecture 9 - Parts.pdf", restricted=False, data=b"%PDF fake"):
    repo, storage = RecordingRepo(), MockStorage("bucket")
    storage.upload("courses/x/file", data, "application/pdf")
    repo.create_material(Material("m1", C272, title, "slides", len(data), "courses/x/file", restricted=restricted))
    ai = ScriptedAI(pages=pages)
    return repo, ai, IngestionService(repo, ai, storage)


def test_pages_become_labelled_embedded_chunks():
    repo, _, ingestion = setup(PAGES)
    ingestion.process_material("m1")

    assert repo.get_material("m1").status == "ready"
    chunks = sorted(repo.list_chunks("m1"), key=lambda c: (c.page, c.content))
    assert [c.page for c in chunks] == [1, 1, 2]
    assert chunks[0].heading == "Lecture 9, page 1 (Slide 1)"
    assert chunks[0].content.startswith("Lecture 9, page 1 (Slide 1). ")
    assert chunks[2].heading == "Lecture 9, page 2"
    assert all(len(c.embedding) == EMBEDDING_SIZE and c.course_id == C272 for c in chunks)


def test_solution_key_chunks_are_restricted():
    repo, _, ingestion = setup(PAGES, title="PS 5 Solutions.pdf", restricted=True)
    ingestion.process_material("m1")
    assert all(c.restricted for c in repo.list_chunks("m1"))


def test_progress_moves_forward_and_ends_on_saving():
    repo, _, ingestion = setup(PAGES)
    ingestion.process_material("m1")
    numbers = [p for p, _ in repo.progress]
    assert numbers == sorted(numbers)
    assert all(1 <= p <= 99 for p in numbers)
    stages = [s for _, s in repo.progress]
    assert stages[0] == "Reading the file"
    assert "Reading page 2 of 2" in stages
    assert "Indexing for search" in stages
    assert stages[-1] == "Saving"


def test_photo_progress_says_photo():
    repo, _, ingestion = setup([TranscribedPage(1, "my handwriting")], title="IMG_0042.jpg")
    ingestion.process_material("m1", "image/jpeg")
    assert "Reading the photo" in [s for _, s in repo.progress]


def test_many_chunks_are_embedded_in_steps():
    pages = [TranscribedPage(i, f"page {i} text") for i in range(1, EMBED_STEP * 2 + 6)]
    repo, ai, ingestion = setup(pages)
    ingestion.process_material("m1")
    document_calls = [n for n, task in ai.embed_calls if task == "document"]
    assert document_calls == [EMBED_STEP, EMBED_STEP, 5]
    assert len(repo.list_chunks("m1")) == len(pages)


def test_retry_replaces_old_chunks():
    repo, _, ingestion = setup(PAGES)
    ingestion.process_material("m1")
    first = {c.id for c in repo.list_chunks("m1")}
    ingestion.process_material("m1")
    second = {c.id for c in repo.list_chunks("m1")}
    assert len(second) == len(first) and not first & second


def test_blank_pages_fail_with_a_reason():
    repo, _, ingestion = setup([TranscribedPage(1, "   "), TranscribedPage(2, "")])
    ingestion.process_material("m1")
    material = repo.get_material("m1")
    assert material.status == "failed"
    assert material.error.startswith("Couldn't find any text")
    assert repo.list_chunks("m1") == []


def test_ai_outage_while_reading_fails_the_file():
    repo, _, ingestion = setup(AIUnavailable("busy"))
    ingestion.process_material("m1")
    assert "busy" in repo.get_material("m1").error


def test_unknown_material_is_ignored():
    repo, _, ingestion = setup(PAGES)
    ingestion.process_material("no-such-material")
    assert repo.get_material("m1").status == "processing"


class FakePdfError(Exception):
    pass


FakePdfError.__module__ = "pypdf.errors"


@pytest.mark.parametrize("error, words", [
    (FileUnreadable("Upload it again."), "Upload it again."),
    (AIUnavailable("busy"), "busy while reading"),
    (FakePdfError("bad xref"), "damaged or password-protected"),
    (ValueError("boom"), "Something went wrong"),
])
def test_failure_reasons(error, words):
    assert words in failure_reason(error)


def test_rate_limit_reason():
    error = AIUnavailable("quota")
    error.rate_limited = True
    assert "usage limit" in failure_reason(error)


@pytest.mark.parametrize("name, mime", [
    ("Lecture 6.pdf", "application/pdf"),
    ("photo.JPG", "image/jpeg"),
    ("work.png", "image/png"),
    ("no-extension", "application/pdf"),
])
def test_guess_mime(name, mime):
    assert guess_mime(name) == mime
