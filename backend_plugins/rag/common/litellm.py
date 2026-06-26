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
        return [row["embedding"] for row in resp.json()["data"]]


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
        return resp.json()
