"""OpenAI-compatible request/response shaping + uniform 'why' surfacing."""
from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import flavors

_log = logging.getLogger("uvicorn.error")

# Snippet length shown per source in the "Retrieved context" details block —
# one product decision, shared by every chunk-returning approach.
SNIPPET_CHARS = 240


class ChatRequest(BaseModel):
    # `model` selects the flavor; `temperature` is accepted for OpenAI-compat (so
    # Open WebUI's payloads validate) but intentionally NOT honored: every approach
    # generates at temperature 0 for a fair side-by-side comparison. `stream=true`
    # is honored with a single-chunk SSE carrying the whole answer (see respond()):
    # LiteLLM proxies these endpoints through the openai SDK, whose streaming
    # decoder yields zero events for a plain JSON body — i.e. an empty answer in a
    # streaming client — so a minimal SSE fallback is required for correctness.
    model: str
    messages: list[dict[str, Any]]
    stream: bool = False
    temperature: float | None = None

    def last_user(self) -> str:
        for msg in reversed(self.messages):
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                # OpenAI multimodal content-parts: join the text parts. str() of
                # the raw list would feed Python-repr garbage to retrieval.
                return " ".join(
                    str(part.get("text") or "")
                    for part in content
                    if isinstance(part, dict) and part.get("type") == "text"
                ).strip()
            return ""  # explicit null or unrecognized shape — never the string "None"
        return ""


@dataclass
class Source:
    title: str
    snippet: str
    score: float | None = None


@dataclass
class Metrics:
    seconds: float
    chunks: int
    llm_calls: int
    cloud_calls: int


def resolve_flavor(req: ChatRequest, base: str) -> flavors.FlavorProfile:
    """Resolve the request's flavor profile for ``base``.

    An unknown model or a flavor bound to a different base is a CLIENT error
    (bad `model` field) — map it to an OpenAI-style 400 instead of letting the
    KeyError surface as an opaque 500.
    """
    try:
        return flavors.get_for_base(req.model, base)
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e.args[0] if e.args else e)) from e


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _render_sources(sources: list[Source]) -> str:
    if not sources:
        return ""
    lines = ["\n\n<details><summary>🔎 Retrieved context "
             f"({_plural(len(sources), 'source')})</summary>\n"]
    for i, s in enumerate(sources, 1):
        score = f" · score {s.score:.3f}" if s.score is not None else ""
        lines.append(f"\n**{i}. {s.title}**{score}\n\n> {s.snippet}\n")
    lines.append("\n</details>")
    return "".join(lines)


def _render_footer(m: Metrics) -> str:
    return (f"\n\n---\n📊 {m.seconds:.1f}s · {_plural(m.chunks, 'chunk')} · "
            f"{_plural(m.llm_calls, 'LLM call')} · {m.cloud_calls} cloud")


def build_response(model: str, answer: str, sources: list[Source],
                   metrics: Metrics, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
    # `answer` is the choke point for every approach. Coerce a non-string answer
    # (e.g. an operator-built n8n workflow that returns a non-string, or a backend
    # that returns structured/list content) to "" so the concatenation below can't
    # raise `list/dict + str` -> 500; sources + metrics still render. Log it —
    # an empty answer with zero diagnostics is undebuggable from the UI.
    if not isinstance(answer, str):
        _log.warning("build_response: coerced non-string answer (%s) for model %s",
                     type(answer).__name__, model)
        answer = ""
    content = answer + _render_sources(sources) + _render_footer(metrics)
    response = {
        # Unique per response; `created` is required by the OpenAI chat.completion
        # schema and strict SDK consumers reject its absence.
        "id": f"ragshow-{model}-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
    if metadata is not None:
        response["rag_showcase"] = metadata
    return response


def build_stream_response(model: str, answer: str, sources: list[Source],
                          metrics: Metrics,
                          metadata: dict[str, Any] | None = None) -> StreamingResponse:
    """Minimal OpenAI-compatible SSE for stream=true clients: one
    chat.completion.chunk carrying the full rendered content, then [DONE]."""
    full = build_response(model, answer, sources, metrics, metadata)
    chunk = {
        "id": full["id"],
        "object": "chat.completion.chunk",
        "created": full["created"],
        "model": model,
        "choices": [{
            "index": 0,
            "delta": {"role": "assistant",
                      "content": full["choices"][0]["message"]["content"]},
            "finish_reason": "stop",
        }],
    }
    if metadata is not None:
        chunk["rag_showcase"] = metadata

    async def gen():
        yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


def respond(req: ChatRequest, model: str, answer: str, sources: list[Source],
            metrics: Metrics, metadata: dict[str, Any] | None = None) -> Any:
    """Uniform response for every approach: honors stream=true with the
    single-chunk SSE fallback, plain JSON otherwise."""
    if req.stream:
        return build_stream_response(model, answer, sources, metrics, metadata)
    return build_response(model, answer, sources, metrics, metadata)
