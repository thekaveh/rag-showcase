"""contextual-rag: same retrieval as hybrid, but over context-prefixed chunks."""
from __future__ import annotations

import asyncio
import time

from fastapi import APIRouter

from ..common import config, flavors, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagContextual"
RETRIEVE_K = 20
TOP_N = 5


@router.post("/contextual-rag/v1/chat/completions")
async def contextual_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = flavors.get_for_base(req.model, "contextual-rag")
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
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    # calls + 1 = chat + embed; the TEI rerank is a cross-encoder (not an LLM/
    # LiteLLM call), so it isn't counted here — its cost surfaces in the latency.
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)
    return build_response(flavor.alias, answer, sources, metrics)
