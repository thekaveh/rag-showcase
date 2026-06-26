"""Client for Atlas's LightRAG server (graph + vector RAG)."""
from __future__ import annotations

import os

import httpx

_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


def _base() -> str:
    return os.environ.get("LIGHTRAG_ENDPOINT", "http://lightrag:9621").rstrip("/")


def _headers() -> dict[str, str]:
    key = os.environ.get("LIGHTRAG_API_KEY", "")
    return {"Authorization": f"Bearer {key}"} if key else {}


async def query(question: str, mode: str = "hybrid") -> str:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_base()}/query", headers=_headers(),
                                 json={"query": question, "mode": mode})
        resp.raise_for_status()
        data = resp.json()
        return data.get("response") or data.get("data") or ""


async def upload_text(title: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_base()}/documents/text", headers=_headers(),
                                 json={"text": text, "description": title})
        resp.raise_for_status()
