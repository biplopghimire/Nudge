"""Processing an uploaded file for the AI (Part 4, "Processing an uploaded file").

Runs in the background after an upload: the material is "processing" until
this finishes, then "ready" (or "failed").

1. The AI transcribes every page (PDF pages or one photo) to clean text, math in LaTeX.
2. Each page is split into chunks of at most 400 words.
3. Each chunk starts with a label like "Lecture 6, page 4 (Substitution)" so search
   can match the file and page.
4. Chunks are embedded and saved with the material's restricted flag.
"""

import logging
import mimetypes
import re
import time

from app.domain import Chunk, Material
from app.integrations.ai import AIClient, AIUnavailable
from app.integrations.storage import StorageClient
from app.repositories.base import Repository
from app.services.common import citation_title, new_id

log = logging.getLogger(__name__)

MAX_CHUNK_WORDS = 400


def split_into_chunks(text: str, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    """Split on blank lines, then cap each piece at max_words."""
    pieces = []
    for section in re.split(r"\n\s*\n", text):
        words = section.split()
        for start in range(0, len(words), max_words):
            pieces.append(" ".join(words[start : start + max_words]))
    return [p for p in pieces if p]


EMBED_STEP = 50  # chunks embedded per progress update


class FileUnreadable(Exception):
    """The file itself is the problem (missing, damaged, no text)."""


def guess_mime(filename: str) -> str:
    return mimetypes.guess_type(filename)[0] or "application/pdf"


def failure_reason(error: Exception) -> str:
    """Why a file failed, in words a teacher can act on."""
    if isinstance(error, FileUnreadable):
        return str(error)
    if isinstance(error, AIUnavailable):
        if getattr(error, "rate_limited", False):
            return "Nudge hit its AI usage limit while reading this file. Tap Retry in a minute."
        return "The AI service was busy while reading this file. Tap Retry to try again."
    if type(error).__module__.startswith("pypdf"):
        return "This PDF couldn't be opened. It may be damaged or password-protected."
    return "Something went wrong while reading this file. Tap Retry to try again."


class IngestionService:
    def __init__(
        self,
        repo: Repository,
        ai: AIClient,
        storage: StorageClient,
        mock_delay_seconds: float = 0.0,
    ):
        self.repo = repo
        self.ai = ai
        self.storage = storage
        self.mock_delay_seconds = mock_delay_seconds

    def process_material(self, material_id: str, mime_type: str | None = None) -> None:
        material = self.repo.get_material(material_id)
        if not material:
            return
        mime_type = mime_type or guess_mime(material.title)
        try:
            if self.mock_delay_seconds:
                time.sleep(self.mock_delay_seconds)  # lets the app show "processing"
            self.repo.delete_chunks(material.id)  # a retry starts clean
            chunks = self._build_chunks(material, mime_type)
            self.repo.set_material_progress(material.id, 99, "Saving")
            self.repo.add_chunks(chunks)
            self.repo.set_material_status(material.id, "ready")
        except Exception as error:
            log.exception("Processing failed for material %s", material.id)
            self.repo.set_material_status(material.id, "failed", failure_reason(error))

    def _progress(self, material_id: str, progress: float, stage: str) -> None:
        self.repo.set_material_progress(material_id, max(1, min(99, round(progress))), stage)

    def _build_chunks(self, material: Material, mime_type: str) -> list[Chunk]:
        data = self.storage.download(material.storage_path)
        if not data:
            raise FileUnreadable("The uploaded file couldn't be found. Upload it again.")
        title = citation_title(material.title)

        # Reading pages is most of the work: 0-75%.
        self._progress(material.id, 2, "Reading the file")

        def on_pages(done: int, total: int) -> None:
            stage = f"Reading page {done} of {total}" if total > 1 else "Reading the photo"
            self._progress(material.id, 2 + 73 * done / max(total, 1), stage)

        drafts: list[tuple[int, str, str]] = []  # (page, heading, content)
        for page in self.ai.transcribe(data, mime_type, on_progress=on_pages):
            heading = f"{title}, page {page.page}" + (f" ({page.heading})" if page.heading else "")
            for piece in split_into_chunks(page.text):
                drafts.append((page.page, heading, f"{heading}. {piece}"))
        if not drafts:
            raise FileUnreadable("Couldn't find any text in this file. If it's a scan, try a clearer copy.")

        # Indexing for search: 75-98%.
        embeddings: list[list[float]] = []
        contents = [content for _, _, content in drafts]
        for start in range(0, len(contents), EMBED_STEP):
            self._progress(material.id, 75 + 23 * start / len(contents), "Indexing for search")
            embeddings += self.ai.embed(contents[start : start + EMBED_STEP], task="document")

        return [
            Chunk(
                id=new_id(),
                course_id=material.course_id,
                material_id=material.id,
                content=content,
                page=page_number,
                heading=heading,
                restricted=material.restricted,
                embedding=embedding,
            )
            for (page_number, heading, content), embedding in zip(drafts, embeddings)
        ]
