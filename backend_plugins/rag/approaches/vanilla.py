"""vanilla-rag: dense top-k retrieve → stuff → one LLM call (the baseline)."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagBase"
K = 5


@router.post("/vanilla-rag/v1/chat/completions")
async def vanilla_rag(req: ChatRequest):
    t0 = time.monotonic()
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    hits = vectors.search_dense(COLLECTION, query_vec, K)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)  # +1 = embed
    return build_response("vanilla-rag", answer, sources, metrics)
