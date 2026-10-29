"""Answering a question with the course's materials (Part 4, "Answering a question").

The same flow runs with the mock or Gemini, and with the in-memory or Postgres
repository: embed the question, search two ways, merge, ask the AI, cite.

Follow-ups like "can I have the answer?" say nothing about the topic, so the
search also runs on the question plus the last few messages, and the earlier
messages go to the AI with it.
"""

from dataclasses import dataclass, replace

from app.domain import Chunk, Citation, Course, Message, Thread
from app.errors import ApiError
from app.integrations.ai import HISTORY_TURNS, AIClient, AIUnavailable, ReplyRequest, Source, Turn
from app.repositories.base import Repository
from app.services.common import citation_title

SEARCH_LIMIT = 20  # results from each search
KEEP = 8           # chunks sent to Gemini
RRF_K = 60         # reciprocal rank fusion constant
CONTEXT_MESSAGES = 3      # earlier messages added to the search for follow-ups
CONTEXT_REPLY_CHARS = 300  # how much of each Nudge reply goes into that search


@dataclass
class EarlierAttachment:
    """The most recent photo or PDF sent earlier in the chat, re-sent so follow-ups can refer to it."""
    message_id: str
    data: bytes
    mime_type: str


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
        earlier_attachment: EarlierAttachment | None = None,
    ) -> Answer:
        settings = course.settings
        if thread.owner_role == "teacher":
            # "Hints only" is for students; teachers get full answers.
            settings = replace(settings, hints_only=False)
        # Solution keys are only searched when the student has sent their own work.
        include_restricted = settings.use_solution_keys and (attachment is not None or earlier_attachment is not None)

        try:
            chunks = self.retrieve(course.id, question, include_restricted, self._search_context(history))
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
                    history=self._turns(history, earlier_attachment),
                )
            )
        except AIUnavailable as error:
            raise ApiError(503, "nudge_busy", "Nudge is busy right now. Try again in a minute.") from error

        used = [s for s in sources if s.number in reply.used_sources]
        citations = self._citations(chunks, used) if settings.cite_materials else []
        return Answer(content=reply.text, citations=citations)

    def retrieve(
        self, course_id: str, question: str, include_restricted: bool, context: str = ""
    ) -> list[Chunk]:
        """Search by meaning and by keyword. With earlier chat, the keyword search and a
        second meaning search use the conversation too, so a follow-up stays on topic,
        while the question's own meaning search still finds a brand-new topic."""
        if not question.strip():
            question = "student work"
        conversation = f"{context}\n{question}" if context else question
        queries = [question, conversation] if context else [question]
        embeddings = self.ai.embed(queries, task="query")
        rankings = [
            self.repo.search_chunks_by_keyword(course_id, conversation, SEARCH_LIMIT, include_restricted),
            *(self.repo.search_chunks_by_embedding(course_id, e, SEARCH_LIMIT, include_restricted) for e in embeddings),
        ]
        return merge_rankings(*rankings)

    @staticmethod
    def _search_context(history: list[Message]) -> str:
        recent = [m for m in history if m.content.strip()][-CONTEXT_MESSAGES:]
        return "\n".join(
            m.content[:CONTEXT_REPLY_CHARS] if m.role == "nudge" else m.content for m in recent
        )

    @staticmethod
    def _turns(history: list[Message], earlier_attachment: EarlierAttachment | None) -> list[Turn]:
        turns = []
        for m in history[-HISTORY_TURNS:]:
            note = {"image": "[sent a photo]", "pdf": "[sent a PDF]"}.get(m.attachment_type or "", "")
            turn = Turn(role=m.role, text=f"{note} {m.content}".strip())
            if earlier_attachment and m.id == earlier_attachment.message_id:
                turn.attachment, turn.attachment_mime = earlier_attachment.data, earlier_attachment.mime_type
            turns.append(turn)
        return turns

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
        """One chip per file name and page the reply relied on. Restricted chunks are never cited."""
        seen: set[tuple[str, int | None]] = set()
        citations = []
        for source in used:
            chunk = chunks[source.number - 1]
            key = (source.title, chunk.page)  # two uploads of the same file show one chip
            if chunk.restricted or key in seen:
                continue
            seen.add(key)
            citations.append(Citation(chunk.material_id, source.title, chunk.page))
        return citations[:3]
