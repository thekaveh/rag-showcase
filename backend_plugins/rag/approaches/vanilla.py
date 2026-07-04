"""vanilla-rag: dense top-k retrieve → stuff → one LLM call (the baseline)."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.openai_io import (ChatRequest, Source, Metrics, SNIPPET_CHARS,
                                resolve_flavor, respond)
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = vectors.BASE_COLLECTION
K = 5


@router.post("/vanilla-rag/v1/chat/completions")
async def vanilla_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = resolve_flavor(req, "vanilla-rag")
    k = int(flavor.params.get("k", K))
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    hits = await asyncio.to_thread(vectors.search_dense, COLLECTION, query_vec, k)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:SNIPPET_CHARS], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)  # +1 = embed
    return respond(req, flavor.alias, answer, sources, metrics)
