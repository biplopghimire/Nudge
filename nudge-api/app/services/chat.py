"""Answering a question with the course's materials (Part 4, "Answering a question").

The same flow runs with the mock or Gemini, and with the in-memory or Postgres
repository: embed the question, search two ways, merge, ask the AI, cite.
"""

from dataclasses import dataclass, replace

from app.domain import Chunk, Citation, Course, Message, Thread
from app.errors import ApiError
from app.integrations.ai import AIClient, AIUnavailable, ReplyRequest, Source
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
        attachment: bytes | None = None,
        attachment_mime: str | None = None,
    ) -> Answer:
        settings = course.settings
        if thread.owner_role == "teacher":
            # "Hints only" is for students; teachers get full answers.
            settings = replace(settings, hints_only=False)
        # Solution keys are only searched when the student sends their own work.
        include_restricted = settings.use_solution_keys and attachment is not None

        try:
            chunks = self.retrieve(course.id, question, include_restricted)
            sources = self._sources(chunks)
            reply = self.ai.generate_reply(
                ReplyRequest(
                    question=question,
                    settings=settings,
                    sources=sources,
                    asker_role=thread.owner_role,
                    assignment_text=self._assignment_text(thread),
                    attachment=attachment,
                    attachment_mime=attachment_mime,
                    history=[(m.role, m.content) for m in history],
                )
            )
        except AIUnavailable as error:
            raise ApiError(503, "nudge_busy", "Nudge is busy right now. Try again in a minute.") from error

        used = [s for s in sources if s.number in reply.used_sources]
        citations = self._citations(chunks, used) if settings.cite_materials else []
        return Answer(content=reply.text, citations=citations)

    def retrieve(self, course_id: str, question: str, include_restricted: bool) -> list[Chunk]:
        if not question.strip():
            question = "student work"
        [embedding] = self.ai.embed([question], task="query")
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

    def _sources(self, chunks: list[Chunk]) -> list[Source]:
        titles: dict[str, str] = {}
        for chunk in chunks:
            if chunk.material_id not in titles:
                material = self.repo.get_material(chunk.material_id)
                titles[chunk.material_id] = citation_title(material.title) if material else "Course material"
        return [
            Source(number=i, title=titles[c.material_id], page=c.page, content=c.content, restricted=c.restricted)
            for i, c in enumerate(chunks, start=1)
        ]

    def _citations(self, chunks: list[Chunk], used: list[Source]) -> list[Citation]:
        """One chip per file and page the reply relied on. Restricted chunks are never cited."""
        seen: set[tuple[str, int | None]] = set()
        citations = []
        for source in used:
            chunk = chunks[source.number - 1]
            key = (chunk.material_id, chunk.page)
            if chunk.restricted or key in seen:
                continue
            seen.add(key)
            citations.append(Citation(chunk.material_id, source.title, chunk.page))
        return citations[:3]
