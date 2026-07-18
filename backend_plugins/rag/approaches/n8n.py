"""n8n-adaptive-rag: bridge Open WebUI <-> an n8n Adaptive-RAG workflow.

The workflow receives {query}, routes by complexity, delegates to another RAG
approach, and returns its structured evidence with the routing decision. This
thin wrapper makes it a selectable OpenAI model without disguising routing
metadata as retrieval evidence.
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import APIRouter

from ..common.openai_io import ChatRequest, Source, Metrics, resolve_flavor, respond

router = APIRouter()
# 240s read budget: the workflow's own two HTTP nodes run sequentially and can take
# up to Classify(60s) + Call Approach(175s) ≈ 235s before n8n returns its shaped
# response (or fallback). The wrapper must wait at least that long — a shorter outer
# timeout would spuriously 500 a slow-but-valid route (e.g. a deep agentic answer).
_TIMEOUT = httpx.Timeout(240.0, connect=10.0)


@router.post("/n8n-adaptive-rag/v1/chat/completions")
async def n8n_adaptive_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = resolve_flavor(req, "n8n-adaptive-rag")
    url = os.environ.get("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json={"query": req.last_user()})
        resp.raise_for_status()
        data = resp.json()
    # the n8n workflow is operator-built; its Respond-to-Webhook node may return a
    # single object or a list of items ("All Incoming Items") — normalize to a
    # dict so .get() is safe instead of raising AttributeError on a list/scalar.
    if isinstance(data, list):
        data = next((d for d in data if isinstance(d, dict)), {})
    elif not isinstance(data, dict):
        data = {}
    extension = data.get("rag_showcase")
    if not isinstance(extension, dict) or extension.get("schema_version") != 1:
        extension = {}

    structured_answer = extension.get("answer")
    answer = data.get("answer") or (structured_answer if isinstance(structured_answer, str) else "")
    route = data.get("route") or "unknown"
    approach = data.get("approach") or "unknown"

    sources: list[Source] = []
    raw_sources = extension.get("sources")
    if isinstance(raw_sources, list):
        for raw in raw_sources:
            if not isinstance(raw, dict) or not isinstance(raw.get("snippet"), str):
                continue
            score = raw.get("score")
            sources.append(Source(
                title=str(raw.get("title") or ""),
                snippet=raw["snippet"],
                score=float(score) if isinstance(score, (int, float)) else None,
            ))

    downstream = extension.get("metrics")
    if not isinstance(downstream, dict):
        downstream = {}
    metrics = Metrics(
        seconds=time.monotonic() - t0,
        chunks=int(downstream.get("chunks") or 0),
        llm_calls=int(downstream.get("llm_calls") or 0) + 1,
        cloud_calls=int(downstream.get("cloud_calls") or 0),
    )
    metadata = {"adaptive": {"route": str(route), "approach": str(approach)}}
    return respond(req, flavor.alias, answer, sources, metrics, metadata=metadata)
