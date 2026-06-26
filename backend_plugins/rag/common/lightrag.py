"""Client for Atlas's LightRAG server (graph + vector RAG)."""
from __future__ import annotations

import logging
import os

import httpx

_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


def _base() -> str:
    return os.environ.get("LIGHTRAG_ENDPOINT", "http://lightrag:9621").rstrip("/")


def _headers() -> dict[str, str]:
    # LightRAG v1.5.0 authenticates the API key via the X-API-Key header;
    # Authorization: Bearer is reserved for JWT login tokens there, so a raw
    # key sent as Bearer 401s whenever LightRAG auth is enabled.
    key = os.environ.get("LIGHTRAG_API_KEY", "")
    return {"X-API-Key": key} if key else {}


async def query(question: str, mode: str = "hybrid") -> str:
    # LightRAG's /query rejects very short queries (min_length=3) with a 422, and
    # a 0–2 char string isn't a meaningful graph question anyway — degrade with a
    # clear message instead of surfacing an unhandled 500.
    if len(question.strip()) < 3:
        return "(query too short for the knowledge graph)"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_base()}/query", headers=_headers(),
                                 json={"query": question, "mode": mode})
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("response") or data.get("data") or ""
        if not answer:
            logging.getLogger("uvicorn.error").warning(
                "lightrag.query returned no recognized answer field (keys=%s)",
                list(data)[:10])
        return answer


async def upload_text(title: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # LightRAG v1.5.0 InsertTextRequest accepts text / file_source / chunking
        # (the optional source label is "file_source", not "description").
        resp = await client.post(f"{_base()}/documents/text", headers=_headers(),
                                 json={"text": text, "file_source": title})
        resp.raise_for_status()
