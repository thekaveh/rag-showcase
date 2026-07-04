"""hybrid-rag: Weaviate hybrid (BM25+dense, relativeScoreFusion) → TEI rerank → stuff."""
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
RETRIEVE_K = 20
TOP_N = 5


@router.post("/hybrid-rag/v1/chat/completions")
async def hybrid_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = resolve_flavor(req, "hybrid-rag")
    retrieve_k = int(flavor.params.get("retrieve_k", RETRIEVE_K))
    top_n = int(flavor.params.get("top_n", TOP_N))
    alpha = float(flavor.params.get("alpha", 0.5))
    rerank = bool(flavor.params.get("rerank", True))
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    candidates = await asyncio.to_thread(
        vectors.search_hybrid, COLLECTION, question, query_vec, retrieve_k, alpha)
    hits = await vectors.rerank(question, candidates, top_n) if rerank else candidates[:top_n]
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:SNIPPET_CHARS], h.score) for h in hits]
    # calls + 1 = chat + embed; the TEI rerank is a cross-encoder (not an LLM/
    # LiteLLM call), so it isn't counted here — its cost surfaces in the latency.
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)
    return respond(req, flavor.alias, answer, sources, metrics)
