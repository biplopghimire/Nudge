"""Stand-ins for Gemini, so tests use mock data and never call the real API.

- FakeGemini answers GeminiClient's HTTP calls through httpx.MockTransport,
  with scripted responses per method, and records every request it gets.
- ScriptedAI is an AIClient with canned replies, titles and transcriptions,
  for testing the services without any HTTP at all.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from app.integrations.ai import AIUnavailable, MockAIClient, Reply, ReplyRequest, TranscribedPage
from app.integrations.gemini import GeminiClient

Responder = httpx.Response | dict | Callable[[httpx.Request], httpx.Response]


def text_response(text: str, finish_reason: str = "STOP") -> dict:
    return {"candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": finish_reason}]}


def json_response(payload: dict) -> dict:
    return text_response(json.dumps(payload))


def error_response(status: int, message: str = "error", retry_delay: str | None = None) -> httpx.Response:
    error: dict = {"message": message}
    if retry_delay:
        error["details"] = [{"retryDelay": retry_delay}]
    return httpx.Response(status, json={"error": error})


def embeddings_for(request: httpx.Request, value: float = 1.0) -> httpx.Response:
    batch = json.loads(request.content)["requests"]
    return httpx.Response(200, json={"embeddings": [{"values": [value] + [0.0] * 767} for _ in batch]})


@dataclass
class Call:
    model: str
    method: str
    body: dict
    headers: httpx.Headers


@dataclass
class FakeGemini:
    """Queue responses per method ("generateContent", "batchEmbedContents"). When a
    method's queue is empty its default answers: a JSON reply, or unit embeddings."""

    queues: dict[str, list[Responder]] = field(default_factory=dict)
    calls: list[Call] = field(default_factory=list)
    default_reply: dict = field(default_factory=lambda: {"reply": "Fake Gemini reply.", "sources": [1]})

    def queue(self, method: str, *responses: Responder) -> "FakeGemini":
        self.queues.setdefault(method, []).extend(responses)
        return self

    def calls_to(self, method: str) -> list[Call]:
        return [c for c in self.calls if c.method == method]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        model, method = request.url.path.split("/models/")[1].split(":")
        self.calls.append(Call(model, method, json.loads(request.content), request.headers))
        queue = self.queues.get(method) or []
        if queue:
            responder = queue.pop(0)
            if callable(responder):
                return responder(request)
            if isinstance(responder, httpx.Response):
                return responder
            return httpx.Response(200, json=responder)
        if method == "batchEmbedContents":
            return embeddings_for(request)
        return httpx.Response(200, json=json_response(self.default_reply))

    def client(self, chat_models: list[str] | None = None, **kwargs) -> GeminiClient:
        return GeminiClient(
            "test-key", chat_models=chat_models or ["chat-model"], transport=httpx.MockTransport(self), **kwargs
        )


class ScriptedAI(MockAIClient):
    """MockAIClient (hashed-word embeddings) with canned answers that tests set."""

    def __init__(
        self,
        reply: Reply | None = None,
        title: str | Exception = "Scripted title",
        pages: list[TranscribedPage] | Exception | None = None,
    ):
        self.reply = reply
        self.title = title
        self.pages = pages
        self.requests: list[ReplyRequest] = []
        self.embed_calls: list[tuple[int, str]] = []

    def embed(self, texts, task="document"):
        self.embed_calls.append((len(texts), task))
        return super().embed(texts, task)

    def generate_reply(self, request: ReplyRequest) -> Reply:
        self.requests.append(request)
        if isinstance(self.reply, Exception):
            raise self.reply
        if self.reply is None:
            return Reply("Scripted reply.", [s.number for s in request.sources])
        return self.reply

    def generate_title(self, question, attachment=None, attachment_mime=None) -> str:
        if isinstance(self.title, Exception):
            raise self.title
        return self.title

    def transcribe(self, data, mime_type, on_progress=None):
        if isinstance(self.pages, Exception):
            raise self.pages
        if self.pages is None:
            return super().transcribe(data, mime_type, on_progress)
        if on_progress:
            for done in range(1, len(self.pages) + 1):
                on_progress(done, len(self.pages))
        return self.pages


def busy() -> AIUnavailable:
    return AIUnavailable("busy")
