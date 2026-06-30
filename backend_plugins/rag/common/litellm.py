"""Thin async client for the LiteLLM gateway (OpenAI-compatible)."""
from __future__ import annotations

from typing import Any

import httpx

from . import config

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


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
        data = resp.json()["data"]
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
    # Per-model request properties from models.yaml (e.g. think:false to suppress a
    # local reasoning model's chain-of-thought). Scoped to this model only; explicit
    # args above win via setdefault, and an unlisted model contributes nothing.
    for _k, _v in config.model_params(model).items():
        payload.setdefault(_k, _v)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.litellm_base()}/v1/chat/completions",
            headers=_headers(), json=payload,
        )
        resp.raise_for_status()
        return resp.json()
