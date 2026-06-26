import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common import contextual
from rag.common.vectors import Hit
from rag.approaches import contextual as contextual_app


@pytest.mark.asyncio
async def test_contextualize_calls_blurb_model(monkeypatch):
    seen = {}
    async def fake_chat(model, messages, **kw):
        seen["model"] = model
        seen["prompt"] = messages[-1]["content"]
        return {"choices": [{"message": {"content": "This chunk is about X."}}]}
    monkeypatch.setattr(contextual.litellm, "chat", fake_chat)
    monkeypatch.setattr(contextual.config, "role", lambda r: "gemma4:31b")
    out = await contextual.contextualize("FULL DOC", "CHUNK")
    assert out == "This chunk is about X."
    assert seen["model"] == "gemma4:31b"
    assert "FULL DOC" in seen["prompt"] and "CHUNK" in seen["prompt"]


@pytest.mark.asyncio
async def test_contextual_route_uses_contextual_collection(monkeypatch):
    # The collection name is the only behavioral differentiator from hybrid-rag;
    # assert the route queries RagContextual (not RagBase).
    seen = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(collection, q, v, k):
        seen["collection"] = collection
        return [Hit("Doc", "ctx body", 0.5)]
    async def fake_rerank(q, hits, top_n): return hits
    async def fake_answer(model, q, hits): return ("ok", 1)
    monkeypatch.setattr(contextual_app.litellm, "embed", fake_embed)
    monkeypatch.setattr(contextual_app.vectors, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(contextual_app.vectors, "rerank", fake_rerank)
    monkeypatch.setattr(contextual_app, "answer_from_context", fake_answer)
    monkeypatch.setattr(contextual_app.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(contextual_app.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/contextual-rag/v1/chat/completions",
                          json={"model": "contextual-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert seen["collection"] == "RagContextual"
