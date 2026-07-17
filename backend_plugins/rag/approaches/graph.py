"""graph-rag: reuse Atlas's LightRAG server (KG + vector dual retrieval)."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import lightrag
from ..common.openai_io import ChatRequest, Source, Metrics, resolve_flavor, respond

router = APIRouter()


@router.post("/graph-rag/v1/chat/completions")
async def graph_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = resolve_flavor(req, "graph-rag")
    answer = await lightrag.query(req.last_user(), profile=flavor.alias)
    sources = [Source("LightRAG knowledge graph", "Graph + vector dual retrieval "
                      f"(profile={flavor.alias}) over the corpus's extracted entities "
                      "and relations.", None)]
    metrics = Metrics(time.monotonic() - t0, 0, 1, 0)
    return respond(
        req,
        flavor.alias,
        answer,
        sources,
        metrics,
        {"lightrag": {"query_profile": flavor.alias}},
    )
