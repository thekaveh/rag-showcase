import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common import contextual
from rag.common import flavors
from rag.common.vectors import Hit
from rag.approaches import contextual as contextual_app


@pytest.fixture(autouse=True)
def _clear_flavor_cache():
    # A per-test flavors.yaml override loads into the module-global cache; clear
    # before AND after so a tmp table can't leak across tests (mirrors siblings).
    flavors._CACHE.clear()
    yield
    flavors._CACHE.clear()


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
    {"choices": [{"message": None}]},               # choice present, null message object
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
async def test_contextualize_logs_and_degrades_on_non_string_content(monkeypatch, caplog):
    # Unlike pipeline.answer_from_context, contextualize has no downstream
    # build_response coercion warning — a non-string content (e.g. a structured
    # content-part list) must be caught and logged here, or a malformed reply
    # silently drops a chunk's blurb with zero diagnostic trail during
    # `python -m ingest.contextual`.
    resp = {"choices": [{"message": {"content": [{"type": "text", "text": "x"}]}}]}
    async def fake_chat(model, messages, **kw): return resp
    monkeypatch.setattr(contextual.litellm, "chat", fake_chat)
    monkeypatch.setattr(contextual.config, "role", lambda r: "stub-blurb-model")
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        out = await contextual.contextualize("doc", "chunk")
    assert out == ""
    assert "non-string" in caplog.text


@pytest.mark.asyncio
async def test_contextual_route_uses_contextual_collection(monkeypatch):
    # The collection name is the only behavioral differentiator from hybrid-rag;
    # assert the route queries RagContextual (not RagBase).
    seen = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(collection, q, v, k, alpha=0.5):
        seen["collection"] = collection; seen["k"] = k
        seen["alpha"] = alpha
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
    assert seen["alpha"] == 0.5
    assert seen["top_n"] == contextual_app.TOP_N
    # generation uses the light_gen role (a wrong key misroutes once roles diverge from the
    # uniform default); cost footer = 1 embed + 1 generation = 2 (the "+1 = embed" convention).
    assert seen["role"] == "light_gen"
    assert "2 LLM calls" in content
    assert "1 chunk" in content  # chunks footer = len(hits), the headline retrieval count


@pytest.mark.asyncio
async def test_contextual_flavor_overrides_params_and_can_skip_rerank(tmp_path, monkeypatch):
    # contextual-rag shares hybrid's tuning surface; pin that its own handler plumbs
    # retrieve_k/alpha/top_n from a flavor and honors rerank:false (previously only
    # hybrid's copy of this code path was exercised).
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: contextual-rag-fast
    base: contextual-rag
    params:
      retrieve_k: 7
      top_n: 2
      alpha: 0.9
      rerank: false
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    calls = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(c, q, v, k, alpha=0.5):
        calls["hybrid"] = (c, k, alpha)
        return [Hit("A", "a", 0.3), Hit("B", "b", 0.2), Hit("C", "c", 0.1)]
    async def forbidden_rerank(q, hits, top_n):
        raise AssertionError("rerank must not be called when the flavor disables it")
    seen = {}
    async def fake_answer(model, q, hits):
        seen["hits"] = hits
        return ("ok", 1)
    monkeypatch.setattr(contextual_app.litellm, "embed", fake_embed)
    monkeypatch.setattr(contextual_app.vectors, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(contextual_app.vectors, "rerank", forbidden_rerank)
    monkeypatch.setattr(contextual_app, "answer_from_context", fake_answer)
    monkeypatch.setattr(contextual_app.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(contextual_app.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/contextual-rag/v1/chat/completions",
                          json={"model": "contextual-rag-fast",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert calls["hybrid"] == ("RagContextual", 7, 0.9)  # flavor params reach retrieval
    assert [h.title for h in seen["hits"]] == ["A", "B"]  # top_n slice, no rerank


def test_doc_window_returns_full_doc_under_the_cap():
    doc = "x" * 100
    assert contextual._doc_window(doc, "x" * 5) == doc


def test_doc_window_centers_on_the_chunk_when_over_the_cap():
    # The chunk must land in the returned window (not just anywhere in doc_text),
    # and the window must be exactly _DOC_WINDOW chars — the function's entire
    # documented purpose ("a window CENTERED on the chunk").
    prefix = "a" * 10_000
    chunk = "THE-CHUNK-MARKER"
    suffix = "b" * 10_000
    doc = prefix + chunk + suffix
    window = contextual._doc_window(doc, chunk)
    assert len(window) == contextual._DOC_WINDOW
    assert chunk in window
    # roughly centered: similar amount of prefix/suffix context on each side
    idx = window.index(chunk)
    before, after = idx, len(window) - idx - len(chunk)
    assert abs(before - after) <= 1


def test_doc_window_falls_back_to_prefix_when_chunk_not_found_verbatim():
    # e.g. a chunk that was re-whitespaced/normalized after extraction no longer
    # appears verbatim in doc_text — must not crash or return an empty/wrong
    # window, just fall back to a plain prefix cut.
    doc = "y" * 20_000
    window = contextual._doc_window(doc, "not present anywhere in doc")
    assert window == doc[: contextual._DOC_WINDOW]
