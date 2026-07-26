"""Thin async client for the LiteLLM gateway (OpenAI-compatible)."""
from __future__ import annotations

import logging
from typing import Any

import httpx

from . import config

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)
_log = logging.getLogger("uvicorn.error")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {config.litellm_key()}",
            "Content-Type": "application/json"}


async def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    model = model or config.role("embed")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.litellm_base()}/v1/embeddings",
            headers=_headers(),
            json={"model": model, "input": texts},
        )
        resp.raise_for_status()
        try:
            body = resp.json()
            data = body.get("data") if isinstance(body, dict) else None
        except ValueError:
            data = None
        if not isinstance(data, list) or not all(
            isinstance(row, dict) and isinstance(row.get("embedding"), list) for row in data
        ):
            # Unlike rerank()/n8n's optional evidence, embeddings are load-bearing —
            # every caller indexes the result positionally (`embed([q])[0]`); a
            # silent [] (or an uncaught AttributeError/KeyError from a malformed
            # row) would surface as a confusing downstream failure instead of this
            # clear, diagnosable one.
            raise RuntimeError(
                f"LiteLLM embeddings gateway returned a malformed response for "
                f"model {model!r} (expected a JSON object with a 'data' list of "
                f"{{'embedding': [...]}} rows)")
        # /v1/embeddings does not guarantee `data` is returned in input order; map
        # back by `index` (as rerank() does) so the positional zip() at the ingest
        # call sites pairs each chunk with its own vector.
        return [row["embedding"] for row in sorted(data, key=lambda r: r.get("index", 0))]


async def chat(model: str, messages: list[dict[str, Any]],
               tools: list[dict] | None = None,
               temperature: float = 0.0) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "messages": messages,
                               "temperature": temperature}
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.litellm_base()}/v1/chat/completions",
            headers=_headers(), json=payload,
        )
        resp.raise_for_status()
        try:
            body = resp.json()
        except ValueError:
            # A 200 with a non-JSON body (upstream Ollama/proxy blip) degrades to an
            # empty dict; both callers already do `resp.get("choices") or []`, which
            # turns this into the same empty-answer path as a response with no
            # choices, instead of an uncaught JSONDecodeError. Log it — an empty
            # `""` answer content is a legitimately-typed str, so it never trips
            # build_response's non-string-answer warning; without a log line here
            # the symptom (bare answer, no text) is otherwise undebuggable.
            _log.warning(
                "litellm chat: gateway returned a non-JSON 200 body for model %r",
                model)
            return {}
        if not isinstance(body, dict):
            _log.warning(
                "litellm chat: gateway returned a non-object 200 body for model %r",
                model)
            return {}
        return body
