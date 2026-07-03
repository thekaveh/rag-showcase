"""Client for Atlas's LightRAG server (graph + vector RAG)."""
from __future__ import annotations

import asyncio
import logging
import os

import httpx

_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


def _base() -> str:
    return os.environ.get("LIGHTRAG_ENDPOINT", "http://lightrag:9621").rstrip("/")


def _headers() -> dict[str, str]:
    # LightRAG v1.5.4 authenticates the API key via the X-API-Key header;
    # Authorization: Bearer is reserved for JWT login tokens there, so a raw
    # key sent as Bearer 401s whenever LightRAG auth is enabled.
    key = os.environ.get("LIGHTRAG_API_KEY", "")
    return {"X-API-Key": key} if key else {}


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return int(raw)


def _query_payload(question: str, mode: str, options: dict | None = None) -> dict:
    options = options or {}
    return {
        "query": question,
        "mode": mode,
        "enable_rerank": options.get(
            "enable_rerank", _env_bool("LIGHTRAG_QUERY_ENABLE_RERANK", False)),
        "top_k": options.get("top_k", _env_int("LIGHTRAG_QUERY_TOP_K", 10)),
        "chunk_top_k": options.get(
            "chunk_top_k", _env_int("LIGHTRAG_QUERY_CHUNK_TOP_K", 5)),
        "max_total_tokens": options.get(
            "max_total_tokens", _env_int("LIGHTRAG_QUERY_MAX_TOTAL_TOKENS", 12000)),
    }


async def query(question: str, mode: str = "hybrid", options: dict | None = None) -> str:
    # LightRAG's /query rejects very short queries (min_length=3) with a 422, and
    # a 0–2 char string isn't a meaningful graph question anyway — degrade with a
    # clear message instead of surfacing an unhandled 500.
    if len(question.strip()) < 3:
        return "(query too short for the knowledge graph)"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_base()}/query", headers=_headers(),
                                 json=_query_payload(question, mode, options))
        resp.raise_for_status()
        data = resp.json()
        answer = data.get("response") or data.get("data") or ""
        if not answer:
            logging.getLogger("uvicorn.error").warning(
                "lightrag.query returned no recognized answer field (keys=%s)",
                list(data)[:10])
        # Honor the -> str contract at this single choke point: if LightRAG ever
        # returns a non-string under response/data, coerce here so BOTH consumers
        # are uniformly protected — graph-rag (via build_response) and agentic-rag
        # (which slices the raw observation, observation[:300]) — instead of only
        # the one that happens to coerce downstream.
        return answer if isinstance(answer, str) else str(answer)


async def upload_text(title: str, text: str) -> None:
    retries = int(os.environ.get("LIGHTRAG_UPLOAD_RETRIES", "60"))
    delay = float(os.environ.get("LIGHTRAG_UPLOAD_RETRY_DELAY", "5"))
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        # LightRAG v1.5.4 InsertTextRequest accepts text / file_source / chunking
        # (the optional source label is "file_source", not "description").
        for attempt in range(retries + 1):
            resp = await client.post(f"{_base()}/documents/text", headers=_headers(),
                                     json={"text": text, "file_source": title})
            if resp.status_code != 409:
                resp.raise_for_status()
                return
            if attempt >= retries:
                resp.raise_for_status()
            logging.getLogger("uvicorn.error").info(
                "LightRAG upload backpressure for %s; retrying in %.1fs (%d/%d)",
                title, delay, attempt + 1, retries)
            await asyncio.sleep(delay)
