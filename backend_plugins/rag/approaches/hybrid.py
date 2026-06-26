"""hybrid-rag: Weaviate hybrid (BM25+dense, RRF) → TEI rerank → stuff."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagBase"
RETRIEVE_K = 20
TOP_N = 5


@router.post("/hybrid-rag/v1/chat/completions")
async def hybrid_rag(req: ChatRequest):
    t0 = time.monotonic()
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    candidates = await asyncio.to_thread(
        vectors.search_hybrid, COLLECTION, question, query_vec, RETRIEVE_K)
    hits = await vectors.rerank(question, candidates, TOP_N)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)
    return build_response("hybrid-rag", answer, sources, metrics)
