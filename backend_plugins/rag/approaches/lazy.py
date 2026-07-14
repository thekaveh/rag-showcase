"""Experimental LazyGraphRAG-style retrieval over a lightweight concept graph."""
from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.lazy_graph import load_or_build, retrieve
from ..common.openai_io import (
    ChatRequest,
    Metrics,
    SNIPPET_CHARS,
    Source,
    resolve_flavor,
    respond,
)
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = vectors.BASE_COLLECTION
RELEVANCE_BUDGET = 24
SEED_K = 8
MAX_CONTEXT_CHUNKS = 8
MAX_CONCEPTS_PER_CHUNK = 24


@router.post("/lazy-graph-rag/v1/chat/completions")
async def lazy_graph_rag(req: ChatRequest):
    started = time.monotonic()
    flavor = resolve_flavor(req, "lazy-graph-rag")
    relevance_budget = int(flavor.params.get("relevance_budget", RELEVANCE_BUDGET))
    seed_k = int(flavor.params.get("seed_k", SEED_K))
    max_context_chunks = int(flavor.params.get("max_context_chunks", MAX_CONTEXT_CHUNKS))
    max_concepts = int(flavor.params.get("max_concepts_per_chunk", MAX_CONCEPTS_PER_CHUNK))
    question = req.last_user()

    query_vector = (await litellm.embed([question]))[0]
    seed_hits, chunks = await asyncio.gather(
        asyncio.to_thread(
            vectors.search_hybrid, COLLECTION, question, query_vector, seed_k, 0.5
        ),
        asyncio.to_thread(vectors.read_chunks, COLLECTION),
    )
    cache_dir = Path(os.getenv("LAZY_GRAPH_CACHE_DIR", "/data/lazy-graph-rag"))
    cache_namespace = f"{COLLECTION}.concepts-{max_concepts}"
    index, build_stats = await asyncio.to_thread(
        load_or_build,
        chunks,
        cache_dir=cache_dir,
        namespace=cache_namespace,
        max_concepts_per_chunk=max_concepts,
    )
    result = await asyncio.to_thread(
        retrieve,
        index,
        question,
        seed_hits=seed_hits,
        relevance_budget=relevance_budget,
        max_context_chunks=max_context_chunks,
    )
    answer, answer_calls = await answer_from_context(
        config.role("light_gen"), question, result.hits
    )
    sources = [
        Source(hit.title, hit.text[:SNIPPET_CHARS], hit.score) for hit in result.hits
    ]
    metadata = {
        "lazy_graph": {
            "experimental": True,
            "cache_hit": build_stats.cache_hit,
            "index_seconds": round(build_stats.index_seconds, 6),
            "graph_chunks": build_stats.chunk_count,
            "graph_concepts": build_stats.concept_count,
            "graph_edges": build_stats.edge_count,
            "relevance_tests": result.relevance_tests,
            "relevance_budget": relevance_budget,
            "seed_k": seed_k,
            "max_context_chunks": max_context_chunks,
            "llm_index_calls": 0,
            "cache_namespace": cache_namespace,
        }
    }
    metrics = Metrics(
        time.monotonic() - started,
        len(result.hits),
        answer_calls + 1,
        0,
    )
    return respond(req, flavor.alias, answer, sources, metrics, metadata)
