"""Processing an uploaded file for the AI (Part 4, "Processing an uploaded file").

Runs in the background after an upload: the material is "processing" until
this finishes, then "ready" (or "failed").
"""

import logging
import re
import time

from app.domain import Chunk, Material
from app.integrations.ai import AIClient
from app.integrations.storage import StorageClient
from app.repositories.base import Repository
from app.services.common import citation_title, new_id

log = logging.getLogger(__name__)

MAX_CHUNK_WORDS = 400


def split_pages(data: bytes, mime_type: str) -> list[bytes]:
    """One image per page.

    TODO: render PDF pages to PNG (for example with pypdfium2). For now the
    whole file counts as one page, which is right for photos.
    """
    return [data]


def split_into_chunks(text: str, max_words: int = MAX_CHUNK_WORDS) -> list[str]:
    """Split on blank lines, then cap each piece at max_words."""
    pieces = []
    for section in re.split(r"\n\s*\n", text):
        words = section.split()
        for start in range(0, len(words), max_words):
            pieces.append(" ".join(words[start : start + max_words]))
    return [p for p in pieces if p]


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

    def process_material(self, material_id: str, mime_type: str = "application/pdf") -> None:
        material = self.repo.get_material(material_id)
        if not material:
            return
        try:
            if self.mock_delay_seconds:
                time.sleep(self.mock_delay_seconds)  # lets the app show "processing"
            chunks = self._build_chunks(material, mime_type)
            self.repo.add_chunks(chunks)
            self.repo.set_material_status(material.id, "ready")
        except Exception:
            log.exception("Processing failed for material %s", material.id)
            self.repo.set_material_status(material.id, "failed")

    def _build_chunks(self, material: Material, mime_type: str) -> list[Chunk]:
        data = self.storage.download(material.storage_path)
        label = citation_title(material.title)
        drafts: list[tuple[int, str]] = []
        for page_number, page in enumerate(split_pages(data, mime_type), start=1):
            text = self.ai.transcribe_page(page, mime_type)
            for piece in split_into_chunks(text):
                # The label helps search match the right file (Part 4).
                drafts.append((page_number, f"{label}, page {page_number}. {piece}"))

        embeddings = self.ai.embed([content for _, content in drafts]) if drafts else []
        return [
            Chunk(
                id=new_id(),
                course_id=material.course_id,
                material_id=material.id,
                content=content,
                page=page_number,
                heading=f"{label}, page {page_number}",
                restricted=material.restricted,
                embedding=embedding,
            )
            for (page_number, content), embedding in zip(drafts, embeddings)
        ]
