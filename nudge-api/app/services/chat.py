"""Answering a question with the course's materials (Part 4, "Answering a question").

This is the real flow. Only the AI client and the repository's search are
mocked, so swapping in Gemini and Postgres needs no changes here.
"""

from dataclasses import dataclass

from app.domain import Chunk, Citation, Course, Message, Thread
from app.integrations.ai import AIClient, ReplyRequest
from app.repositories.base import Repository
from app.services.common import citation_title

SEARCH_LIMIT = 20  # results from each search
KEEP = 8           # chunks sent to Gemini
RRF_K = 60         # reciprocal rank fusion constant


@dataclass
class Answer:
    content: str
    citations: list[Citation]


def merge_rankings(*rankings: list[Chunk], keep: int = KEEP) -> list[Chunk]:
    """Reciprocal rank fusion: a chunk ranked well in both lists comes first."""
    scores: dict[str, float] = {}
    by_id: dict[str, Chunk] = {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (RRF_K + rank + 1)
            by_id[chunk.id] = chunk
    best = sorted(scores, key=scores.get, reverse=True)[:keep]
    return [by_id[chunk_id] for chunk_id in best]


class ChatService:
    def __init__(self, repo: Repository, ai: AIClient):
        self.repo = repo
        self.ai = ai

    def answer(
        self,
        thread: Thread,
        course: Course,
        question: str,
        history: list[Message],
        photo: bytes | None = None,
        photo_mime: str | None = None,
    ) -> Answer:
        settings = course.settings
        # Solution keys are only searched when the student sends their own work.
        include_restricted = settings.use_solution_keys and photo is not None

        chunks = self.retrieve(course.id, question, include_restricted)
        reply = self.ai.generate_reply(
            ReplyRequest(
                question=question,
                settings=settings,
                chunks=chunks,
                assignment_text=self._assignment_text(thread),
                photo=photo,
                photo_mime=photo_mime,
                history=[(m.role, m.content) for m in history],
            )
        )
        citations = self._citations(chunks) if settings.cite_materials else []
        return Answer(content=reply, citations=citations)

    def retrieve(self, course_id: str, question: str, include_restricted: bool) -> list[Chunk]:
        if not question.strip():
            question = "student work"
        [embedding] = self.ai.embed([question])
        by_meaning = self.repo.search_chunks_by_embedding(
            course_id, embedding, SEARCH_LIMIT, include_restricted
        )
        by_keyword = self.repo.search_chunks_by_keyword(
            course_id, question, SEARCH_LIMIT, include_restricted
        )
        return merge_rankings(by_keyword, by_meaning)

    def _assignment_text(self, thread: Thread) -> str | None:
        if not thread.assignment_id:
            return None
        assignment = self.repo.get_assignment(thread.assignment_id)
        if not assignment or not assignment.material_id:
            return None
        chunks = sorted(self.repo.list_chunks(assignment.material_id), key=lambda c: c.page or 0)
        return "\n\n".join(c.content for c in chunks) or None

    def _citations(self, chunks: list[Chunk]) -> list[Citation]:
        """One citation per file and page. Restricted chunks are never cited."""
        seen: set[tuple[str, int | None]] = set()
        citations = []
        for chunk in chunks:
            key = (chunk.material_id, chunk.page)
            if chunk.restricted or key in seen:
                continue
            material = self.repo.get_material(chunk.material_id)
            if not material:
                continue
            seen.add(key)
            citations.append(Citation(chunk.material_id, citation_title(material.title), chunk.page))
        return citations[:3]
