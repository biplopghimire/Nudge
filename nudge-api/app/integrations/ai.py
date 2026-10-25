"""Gemini. The interface the services use, plus a mock that needs no API key.

The real version (GeminiClient) should:
- embed: gemini-embedding-2 with output_dimensionality=768
- transcribe_page: send a page image and ask for clean text, math in LaTeX
- generate_reply: send SYSTEM_RULES, course settings, chunks, assignment text,
  the student's photo and the question
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.domain import Chunk, CourseSettings

EMBEDDING_SIZE = 768

SYSTEM_RULES = """\
Use only the course material provided.
Use the same notation and methods as the course material.
Cite the file and page for each point.
If the material does not cover the question, say so instead of guessing.
"""
HINTS_ONLY_RULE = "Give hints and questions, never the final answer."


@dataclass
class ReplyRequest:
    question: str
    settings: CourseSettings
    chunks: list[Chunk]
    assignment_text: str | None = None
    photo: bytes | None = None
    photo_mime: str | None = None
    history: list[tuple[str, str]] = field(default_factory=list)  # (role, content), oldest first


class AIClient(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def transcribe_page(self, page: bytes, mime_type: str) -> str: ...

    @abstractmethod
    def generate_reply(self, request: ReplyRequest) -> str: ...


class MockAIClient(AIClient):
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * EMBEDDING_SIZE for _ in texts]

    def transcribe_page(self, page: bytes, mime_type: str) -> str:
        return "(mock transcription) Page text would appear here."

    def generate_reply(self, request: ReplyRequest) -> str:
        if not request.chunks:
            return (
                "I couldn't find this in your course materials. "
                "Try asking your teacher or bringing it to office hours."
            )
        source = request.chunks[0].heading or "the course material"
        if request.photo:
            opener = "Thanks for the photo of your work."
        else:
            opener = "Good question."
        if request.settings.hints_only:
            return f"{opener} Look at {source}. What is the first step it shows for a problem like this?"
        return f"{opener} {source} covers this: {request.chunks[0].content[:200]}"
