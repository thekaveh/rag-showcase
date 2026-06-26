"""graph-rag: reuse Atlas's LightRAG server (KG + vector dual retrieval)."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import lightrag
from ..common.openai_io import ChatRequest, Source, Metrics, build_response

router = APIRouter()


@router.post("/graph-rag/v1/chat/completions")
async def graph_rag(req: ChatRequest):
    t0 = time.monotonic()
    answer = await lightrag.query(req.last_user(), mode="hybrid")
    sources = [Source("LightRAG knowledge graph", "Graph + vector dual retrieval "
                      "(mode=hybrid) over the corpus's extracted entities & relations.", None)]
    metrics = Metrics(time.monotonic() - t0, 0, 1, 0)
    return build_response("graph-rag", answer, sources, metrics)
