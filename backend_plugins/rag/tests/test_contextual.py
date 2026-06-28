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
    def fake_role(r): seen["role"] = r; return "stub-blurb-model"
    monkeypatch.setattr(contextual.litellm, "chat", fake_chat)
    monkeypatch.setattr(contextual.config, "role", fake_role)
    out = await contextual.contextualize("FULL DOC", "CHUNK")
    assert out == "This chunk is about X."
    assert seen["model"] == "stub-blurb-model"
    assert seen["role"] == "contextual_blurb"  # the blurb uses its own dedicated role key
    assert "FULL DOC" in seen["prompt"] and "CHUNK" in seen["prompt"]


@pytest.mark.asyncio
@pytest.mark.parametrize("resp", [
    {"choices": []},                                # gateway returned no choices
    {},                                             # malformed: no choices key at all
    {"choices": [{"message": {"content": None}}]},  # choice present, null content
    {"choices": [{"message": {}}]},                 # choice present, no content key
])
async def test_contextualize_degrades_to_empty_string(monkeypatch, resp):
    # the blurb reply is parsed with the same guard-and-degrade idiom as
    # answer_from_context: a malformed/empty gateway reply must yield "" — never
    # None, never an AttributeError at .strip(). Drop the guards and ingest.py's
    # f"{blurb}\n\n{text}" either embeds the literal "None" or crashes the whole
    # corpus run, with no test failing. So pin the degrade explicitly.
    async def fake_chat(model, messages, **kw): return resp
    monkeypatch.setattr(contextual.litellm, "chat", fake_chat)
    monkeypatch.setattr(contextual.config, "role", lambda r: "stub-blurb-model")
    assert await contextual.contextualize("doc", "chunk") == ""


@pytest.mark.asyncio
async def test_contextual_route_uses_contextual_collection(monkeypatch):
    # The collection name is the only behavioral differentiator from hybrid-rag;
    # assert the route queries RagContextual (not RagBase).
    seen = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(collection, q, v, k):
        seen["collection"] = collection; seen["k"] = k
        return [Hit("Doc", "ctx body", 0.5)]
    async def fake_rerank(q, hits, top_n): seen["top_n"] = top_n; return hits
    async def fake_answer(model, q, hits): return ("ok", 1)
    def fake_role(r): seen["role"] = r; return "qwen3.6"
    monkeypatch.setattr(contextual_app.litellm, "embed", fake_embed)
    monkeypatch.setattr(contextual_app.vectors, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(contextual_app.vectors, "rerank", fake_rerank)
    monkeypatch.setattr(contextual_app, "answer_from_context", fake_answer)
    monkeypatch.setattr(contextual_app.config, "role", fake_role)

    app = FastAPI(); app.include_router(contextual_app.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/contextual-rag/v1/chat/completions",
                          json={"model": "contextual-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert seen["collection"] == "RagContextual"  # the ONLY differentiator from hybrid-rag
    # same retrieval wiring as hybrid: the full RETRIEVE_K pool feeds the reranker, which
    # runs at TOP_N — passing TOP_N to search_hybrid would silently shrink the pool 20->5.
    assert seen["k"] == contextual_app.RETRIEVE_K
    assert seen["top_n"] == contextual_app.TOP_N
    # generation uses the light_gen role (a wrong key misroutes once roles diverge from the
    # uniform default); cost footer = 1 embed + 1 generation = 2 (the "+1 = embed" convention).
    assert seen["role"] == "light_gen"
    assert "2 LLM calls" in content
    assert "1 chunk" in content  # chunks footer = len(hits), the headline retrieval count
