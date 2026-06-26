"""n8n-adaptive-rag: bridge OpenWebUI <-> an n8n Adaptive-RAG workflow.

The workflow (built visually in n8n) receives {query}, routes by complexity,
retrieves, generates, and returns {answer, route}. This thin wrapper makes it
a selectable OpenAI model.
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import APIRouter

from ..common.openai_io import ChatRequest, Source, Metrics, build_response

router = APIRouter()
_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


@router.post("/n8n-adaptive-rag/v1/chat/completions")
async def n8n_adaptive_rag(req: ChatRequest):
    t0 = time.monotonic()
    url = os.environ.get("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json={"query": req.last_user()})
        resp.raise_for_status()
        data = resp.json()
    answer = data.get("answer", "")
    route = data.get("route", "unknown")
    sources = [Source("🧭 Adaptive route", f"n8n routed this query as **{route}**.", None)]
    metrics = Metrics(time.monotonic() - t0, 0, 1, 0)
    return build_response("n8n-adaptive-rag", answer, sources, metrics)
