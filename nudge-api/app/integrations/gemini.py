"""Gemini over its REST API (https://ai.google.dev/api).

Gemini sometimes answers "503 high demand" or hangs, so every call has a
timeout and moves straight on to the next model in its list when one is busy.
If every model fails, it waits briefly and makes one more pass.
"""

import base64
import io
import json
import logging
import math
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.integrations.ai import (
    EMBEDDING_SIZE,
    AIClient,
    AIUnavailable,
    EmbedTask,
    Reply,
    ReplyRequest,
    TranscribedPage,
    build_instructions,
    format_sources,
)

log = logging.getLogger(__name__)

BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
RETRY_STATUSES = {429, 500, 502, 503, 504}
EMBED_BATCH = 50        # texts per batchEmbedContents call (each text counts toward the per-minute limit)
EMBED_RATE_LIMIT_RETRIES = 6  # an upload waits out up to ~6 minutes of rate limiting
PAGES_PER_PART = 8      # PDF pages sent per transcription call
HISTORY_TURNS = 12      # earlier messages sent with each question

TRANSCRIBE_PROMPT = """\
Transcribe every page of this course document into clean text for a search index.
- Keep all words, including slide titles, bullet points, problem statements and captions.
- Write math in LaTeX ($...$). Describe diagrams and charts in one sentence in [brackets].
- For handwriting, transcribe what is written; mark unreadable parts as [unclear].
- "heading" is the page's title, slide title or problem number, or null.
Return one entry per page, numbered from {first_page}, in order."""

TRANSCRIBE_SCHEMA = {
    "type": "object",
    "properties": {
        "pages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "page": {"type": "integer"},
                    "heading": {"type": "string", "nullable": True},
                    "text": {"type": "string"},
                },
                "required": ["page", "text"],
            },
        }
    },
    "required": ["pages"],
}

REPLY_SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string"},
        "sources": {"type": "array", "items": {"type": "integer"}},
    },
    "required": ["reply", "sources"],
}

TASK_TYPES = {"document": "RETRIEVAL_DOCUMENT", "query": "RETRIEVAL_QUERY"}


class GeminiError(AIUnavailable):
    def __init__(self, message: str, retryable: bool = False, status: int | None = None,
                 retry_after: float | None = None):
        super().__init__(message)
        self.retryable = retryable
        self.status = status
        self.retry_after = retry_after  # seconds Gemini asked us to wait, if it said

    @property
    def rate_limited(self) -> bool:
        return self.status == 429


def _retry_delay(error_body: dict) -> float | None:
    """Gemini puts 'retry in 47s' in a RetryInfo detail on 429s."""
    for detail in error_body.get("details", []) or []:
        delay = str(detail.get("retryDelay", ""))
        if delay.endswith("s"):
            try:
                return float(delay[:-1])
            except ValueError:
                pass
    return None


def _normalize(vector: list[float]) -> list[float]:
    # Gemini only normalizes full-size embeddings; cosine search expects unit length.
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def _inline(data: bytes, mime_type: str) -> dict:
    return {"inline_data": {"mime_type": mime_type, "data": base64.b64encode(data).decode()}}


def _text_of(response: dict) -> str:
    candidate = (response.get("candidates") or [{}])[0]
    parts = (candidate.get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not text:
        raise GeminiError(f"Gemini returned no text (finishReason: {candidate.get('finishReason', 'none')})")
    return text


def page_count(data: bytes) -> int:
    from pypdf import PdfReader

    return len(PdfReader(io.BytesIO(data)).pages)


def split_pdf(data: bytes, pages_per_part: int = PAGES_PER_PART) -> list[tuple[int, bytes]]:
    """[(first page number, PDF bytes)] in parts of at most `pages_per_part` pages."""
    from pypdf import PdfReader, PdfWriter

    reader = PdfReader(io.BytesIO(data))
    if len(reader.pages) <= pages_per_part:
        return [(1, data)]
    parts = []
    for start in range(0, len(reader.pages), pages_per_part):
        writer = PdfWriter()
        for page in reader.pages[start : start + pages_per_part]:
            writer.add_page(page)
        out = io.BytesIO()
        writer.write(out)
        parts.append((start + 1, out.getvalue()))
    return parts


class GeminiClient(AIClient):
    def __init__(
        self,
        api_key: str,
        chat_models: list[str],
        transcribe_models: list[str] | None = None,
        embedding_model: str = "gemini-embedding-2",
        timeout_seconds: float = 60.0,
        transcribe_timeout_seconds: float = 180.0,
        passes: int = 2,
        transport: httpx.BaseTransport | None = None,  # tests pass a fake
    ):
        if not chat_models:
            raise ValueError("Give at least one Gemini chat model.")
        self.chat_models = chat_models
        self.transcribe_models = transcribe_models or chat_models
        self.embedding_model = embedding_model
        self.timeout = timeout_seconds
        self.transcribe_timeout = transcribe_timeout_seconds
        self.passes = passes
        self.http = httpx.Client(base_url=BASE_URL, headers={"x-goog-api-key": api_key}, transport=transport)

    # ---- HTTP with retries and model fallback ----

    def _post_once(self, model: str, method: str, body: dict, timeout: float) -> dict:
        """One request. Raises GeminiError; `.retryable` says whether another try may work."""
        try:
            response = self.http.post(f"/models/{model}:{method}", json=body, timeout=timeout)
        except httpx.TimeoutException:
            raise GeminiError(f"{model} timed out after {timeout:.0f}s", retryable=True)
        except httpx.HTTPError as error:
            raise GeminiError(f"{model} request failed: {error}", retryable=True)
        if response.status_code == 200:
            return response.json()
        try:
            error_body = response.json().get("error", {})
        except ValueError:
            error_body = {"message": response.text[:200]}
        raise GeminiError(
            f"{model} {response.status_code}: {error_body.get('message', '')}",
            retryable=response.status_code in RETRY_STATUSES,
            status=response.status_code,
            retry_after=_retry_delay(error_body),
        )

    def _call(self, models: list[str], method: str, body: dict, timeout: float) -> dict:
        """Try each model once per pass until one answers."""
        errors: list[str] = []
        for attempt in range(self.passes):
            if attempt:
                time.sleep(2.0 * attempt)
            for model in models:
                try:
                    return self._post_once(model, method, body, timeout)
                except GeminiError as error:
                    errors.append(str(error))
                    log.warning("Gemini %s", error)
                    if not error.retryable:
                        raise
        raise GeminiError("Gemini is unavailable right now: " + " | ".join(errors[-3:]), retryable=True)

    # ---- embeddings ----

    def embed(self, texts: list[str], task: EmbedTask = "document") -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start : start + EMBED_BATCH]
            body = {
                "requests": [
                    {
                        "model": f"models/{self.embedding_model}",
                        "content": {"parts": [{"text": text or " "}]},
                        "taskType": TASK_TYPES[task],
                        "outputDimensionality": EMBEDDING_SIZE,
                    }
                    for text in batch
                ]
            }
            if task == "document":
                response = self._embed_patiently(body)
            else:
                response = self._call([self.embedding_model], "batchEmbedContents", body, self.timeout)
            vectors += [_normalize(e["values"]) for e in response["embeddings"]]
        return vectors

    def _embed_patiently(self, body: dict) -> dict:
        """Embedding a whole upload can pass the per-minute limit (100 texts a minute on the
        free tier). Uploads are processed in the background, so wait out the limit and retry
        instead of failing the file."""
        for attempt in range(EMBED_RATE_LIMIT_RETRIES + 1):
            try:
                return self._post_once(self.embedding_model, "batchEmbedContents", body, self.timeout)
            except GeminiError as error:
                if not error.retryable or attempt == EMBED_RATE_LIMIT_RETRIES:
                    raise
                if error.rate_limited:
                    wait = min(error.retry_after or 15.0 * (attempt + 1), 70.0)
                else:
                    wait = 2.0 * (attempt + 1)
                log.warning("Gemini embeddings %s; waiting %.0fs (attempt %d)", error.status, wait, attempt + 1)
                time.sleep(wait)
        raise AssertionError("unreachable")

    # ---- transcription ----

    def transcribe(
        self, data: bytes, mime_type: str, on_progress: Callable[[int, int], None] | None = None
    ) -> list[TranscribedPage]:
        parts = split_pdf(data) if mime_type == "application/pdf" else [(1, data)]
        total_pages = page_count(data) if mime_type == "application/pdf" else 1
        pages: list[TranscribedPage] = []
        for first_page, part in parts:
            body = {
                "contents": [{
                    "role": "user",
                    "parts": [_inline(part, mime_type), {"text": TRANSCRIBE_PROMPT.format(first_page=first_page)}],
                }],
                "generationConfig": {
                    "temperature": 0,
                    "responseMimeType": "application/json",
                    "responseSchema": TRANSCRIBE_SCHEMA,
                },
            }
            response = self._call(self.transcribe_models, "generateContent", body, self.transcribe_timeout)
            result = json.loads(_text_of(response))
            for i, page in enumerate(result.get("pages", [])):
                pages.append(
                    TranscribedPage(
                        # Trust our own numbering over the model's if they disagree.
                        page=first_page + i,
                        text=(page.get("text") or "").strip(),
                        heading=(page.get("heading") or None),
                    )
                )
            if on_progress:
                on_progress(min(first_page - 1 + PAGES_PER_PART, total_pages), total_pages)
        return pages

    # ---- replies ----

    def generate_reply(self, request: ReplyRequest) -> Reply:
        contents: list[dict[str, Any]] = []
        for role, text in request.history[-HISTORY_TURNS:]:
            if text.strip():
                contents.append({"role": "model" if role == "nudge" else "user", "parts": [{"text": text}]})

        prompt = [format_sources(request.sources)]
        if request.assignment_text:
            prompt.append(f"CURRENT ASSIGNMENT (the chat is about this):\n{request.assignment_text}")
        question = request.question or "Here is my work. Can you check it?"
        prompt.append(f"QUESTION:\n{question}")
        parts: list[dict] = [{"text": "\n\n".join(prompt)}]
        if request.attachment and request.attachment_mime:
            parts.append(_inline(request.attachment, request.attachment_mime))
        contents.append({"role": "user", "parts": parts})

        body = {
            "systemInstruction": {"parts": [{"text": build_instructions(request)}]},
            "contents": contents,
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
                "responseSchema": REPLY_SCHEMA,
            },
        }
        raw = _text_of(self._call(self.chat_models, "generateContent", body, self.timeout))
        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            return Reply(raw, [])  # still show the reply if the JSON was malformed
        numbers = {s.number for s in request.sources if not s.restricted}
        used = [n for n in result.get("sources", []) if n in numbers]
        return Reply(result.get("reply", "").strip() or raw, used)
