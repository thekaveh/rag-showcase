import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import hybrid


@pytest.mark.asyncio
async def test_hybrid_uses_hybrid_search_then_rerank(monkeypatch):
    calls = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(c, q, v, k, alpha=0.5):
        calls["hybrid"] = (q, k); calls["alpha"] = alpha; calls["collection"] = c
        return [Hit("A", "a", 0.1), Hit("B", "KEYWORD body", 0.2)]
    async def fake_rerank(q, hits, top_n):
        calls["rerank"] = top_n
        return [hits[1]]  # the KEYWORD hit floats to top
    async def fake_answer(model, q, hits): return ("ok", 1)
    monkeypatch.setattr(hybrid.litellm, "embed", fake_embed)
    monkeypatch.setattr(hybrid.vectors, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(hybrid.vectors, "rerank", fake_rerank)
    monkeypatch.setattr(hybrid, "answer_from_context", fake_answer)
    def fake_role(r): calls["role"] = r; return "qwen3.6"
    monkeypatch.setattr(hybrid.config, "role", fake_role)

    app = FastAPI(); app.include_router(hybrid.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/hybrid-rag/v1/chat/completions",
                          json={"model": "hybrid-rag",
                                "messages": [{"role": "user", "content": "find KEYWORD"}]})
    assert r.status_code == 200
    assert calls["hybrid"][0] == "find KEYWORD"   # raw text drives BM25 leg
    assert calls["hybrid"][1] == hybrid.RETRIEVE_K  # the FULL candidate pool (20) feeds
    assert calls["alpha"] == 0.5                  # default flavor preserves equal weighting
    #   the reranker — passing TOP_N (5) here would silently shrink the pool, degrading
    #   rerank quality while every other assertion stays green.
    assert calls["rerank"] == hybrid.TOP_N         # rerank runs with the configured top_n
    content = r.json()["choices"][0]["message"]["content"]
    assert "KEYWORD" in content
    # hybrid-rag's ONLY differentiator from contextual-rag is the collection it queries:
    # RagBase (plain chunks) vs RagContextual (blurb-prefixed). Flip hybrid.COLLECTION to
    # RagContextual and the two become retrieval-identical, collapsing the showcase's
    # central "does contextual beat plain hybrid?" contrast — every test still green. Pin it.
    assert calls["collection"] == "RagBase"
    # cost footer: 1 embed + 1 generation = 2 (guards the "+1 = embed" convention).
    assert "2 LLM calls" in content
    assert calls["role"] == "light_gen"  # generation uses the light_gen role
    assert "1 chunk" in content           # chunks footer = len(hits), the headline retrieval count


@pytest.mark.asyncio
async def test_hybrid_flavor_overrides_retrieval_params(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: hybrid-rag-high-recall
    base: hybrid-rag
    params:
      retrieve_k: 40
      top_n: 8
      alpha: 0.25
""",
        encoding="utf-8",
    )
    hybrid.flavors._CACHE.clear()
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    calls = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(c, q, v, k, alpha=0.5):
        calls["hybrid"] = (k, alpha)
        return [Hit("A", "a", 0.1), Hit("B", "b", 0.2)]
    async def fake_rerank(q, hits, top_n):
        calls["rerank"] = top_n
        return hits
    async def fake_answer(model, q, hits): return ("ok", 1)
    monkeypatch.setattr(hybrid.litellm, "embed", fake_embed)
    monkeypatch.setattr(hybrid.vectors, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(hybrid.vectors, "rerank", fake_rerank)
    monkeypatch.setattr(hybrid, "answer_from_context", fake_answer)
    monkeypatch.setattr(hybrid.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(hybrid.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/hybrid-rag/v1/chat/completions",
                          json={"model": "hybrid-rag-high-recall",
                                "messages": [{"role": "user", "content": "find KEYWORD"}]})

    assert r.status_code == 200
    assert calls["hybrid"] == (40, 0.25)
    assert calls["rerank"] == 8
