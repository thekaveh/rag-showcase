"""vanilla-rag: dense top-k retrieve → stuff → one LLM call (the baseline)."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter

from ..common import config, flavors, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagBase"
K = 5


@router.post("/vanilla-rag/v1/chat/completions")
async def vanilla_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = flavors.get_for_base(req.model, "vanilla-rag")
    k = int(flavor.params.get("k", K))
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    hits = await asyncio.to_thread(vectors.search_dense, COLLECTION, query_vec, k)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)  # +1 = embed
    return build_response(flavor.alias, answer, sources, metrics)
