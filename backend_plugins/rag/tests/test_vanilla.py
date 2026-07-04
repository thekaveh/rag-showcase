import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.common import flavors
from rag.approaches import vanilla


@pytest.fixture(autouse=True)
def _clear_flavor_cache():
    # A per-test flavors.yaml override loads into the module-global cache; clear
    # before AND after so a tmp table can't leak across tests (mirrors siblings).
    flavors._CACHE.clear()
    yield
    flavors._CACHE.clear()


@pytest.mark.asyncio
async def test_vanilla_retrieves_and_answers(monkeypatch):
    async def fake_embed(texts, model=None): return [[0.0, 1.0]]
    async def fake_chat(model, messages, **kw):
        # the user's question must reach the model with context appended
        joined = messages[-1]["content"]
        assert "CTX-ALPHA" in joined
        return {"choices": [{"message": {"content": "answered"}}]}
    monkeypatch.setattr(vanilla.litellm, "embed", fake_embed)
    monkeypatch.setattr(vanilla.litellm, "chat", fake_chat)
    seen = {}
    def fake_dense(c, v, k):
        seen["collection"] = c
        return [Hit("Doc", "CTX-ALPHA body", 0.2)]
    monkeypatch.setattr(vanilla.vectors, "search_dense", fake_dense)
    def fake_role(r): seen["role"] = r; return "qwen3.6"
    monkeypatch.setattr(vanilla.config, "role", fake_role)

    app = FastAPI(); app.include_router(vanilla.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/vanilla-rag/v1/chat/completions",
                          json={"model": "vanilla-rag",
                                "messages": [{"role": "user", "content": "what is alpha?"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "answered" in content and "Doc" in content  # answer + sources block
    assert seen["collection"] == "RagBase"  # the baseline retrieves from the base index
    assert seen["role"] == "light_gen"      # generation uses the light_gen role
    # cost footer: 1 embed + 1 generation = 2 (guards the "+1 = embed" convention the
    # showcase's cost comparison depends on — drop the +1 and this drops to "1 LLM call").
    assert "2 LLM calls" in content
    assert "1 chunk" in content  # chunks footer = len(hits); flip to the delegating
    #   approaches' constant 0 and it misreports the headline retrieval count, suite green.


@pytest.mark.asyncio
async def test_vanilla_flavor_overrides_k(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: vanilla-rag-one
    base: vanilla-rag
    params:
      k: 1
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    seen = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_dense(c, v, k):
        seen["k"] = k
        return [Hit("Doc", "body", 0.2)]
    async def fake_chat(model, messages, **kw):
        return {"choices": [{"message": {"content": "ok"}}]}
    monkeypatch.setattr(vanilla.litellm, "embed", fake_embed)
    monkeypatch.setattr(vanilla.litellm, "chat", fake_chat)
    monkeypatch.setattr(vanilla.vectors, "search_dense", fake_dense)
    monkeypatch.setattr(vanilla.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(vanilla.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/vanilla-rag/v1/chat/completions",
                          json={"model": "vanilla-rag-one",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert seen["k"] == 1  # the flavor's k, not the module default of 5


@pytest.mark.asyncio
async def test_unknown_or_mismatched_model_maps_to_400_not_500():
    # A bad `model` field is a CLIENT error: unknown aliases and flavors bound to a
    # different base must map to an OpenAI-style 400, not an opaque KeyError 500.
    app = FastAPI(); app.include_router(vanilla.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        unknown = await ac.post("/vanilla-rag/v1/chat/completions",
                                json={"model": "nope-rag",
                                      "messages": [{"role": "user", "content": "q"}]})
        mismatched = await ac.post("/vanilla-rag/v1/chat/completions",
                                   json={"model": "hybrid-rag",
                                         "messages": [{"role": "user", "content": "q"}]})
    assert unknown.status_code == 400
    assert "nope-rag" in unknown.json()["detail"]
    assert mismatched.status_code == 400
    assert "hybrid-rag" in mismatched.json()["detail"]


@pytest.mark.asyncio
async def test_stream_true_returns_single_chunk_sse(monkeypatch):
    # LiteLLM proxies these endpoints through the openai SDK: for stream=true a
    # plain JSON body decodes to ZERO SSE events (an empty answer in Open WebUI).
    # The handler must emit a real SSE stream carrying the whole content.
    async def fake_embed(texts, model=None): return [[1.0]]
    async def fake_chat(model, messages, **kw):
        return {"choices": [{"message": {"content": "streamed answer"}}]}
    monkeypatch.setattr(vanilla.litellm, "embed", fake_embed)
    monkeypatch.setattr(vanilla.litellm, "chat", fake_chat)
    monkeypatch.setattr(vanilla.vectors, "search_dense",
                        lambda c, v, k: [Hit("Doc", "body", 0.2)])
    monkeypatch.setattr(vanilla.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(vanilla.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/vanilla-rag/v1/chat/completions",
                          json={"model": "vanilla-rag", "stream": True,
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")
    assert "streamed answer" in r.text
    assert '"chat.completion.chunk"' in r.text
    assert r.text.rstrip().endswith("data: [DONE]")


@pytest.mark.asyncio
async def test_realistic_openwebui_payload_with_extra_fields_is_accepted(monkeypatch):
    # Real clients (Open WebUI via LiteLLM) send fields beyond our model — e.g.
    # max_tokens and stream_options. Pydantic must keep ignoring extras: a future
    # extra="forbid" would 422 every real client with the rest of the suite green.
    async def fake_embed(texts, model=None): return [[1.0]]
    async def fake_chat(model, messages, **kw):
        return {"choices": [{"message": {"content": "ok"}}]}
    monkeypatch.setattr(vanilla.litellm, "embed", fake_embed)
    monkeypatch.setattr(vanilla.litellm, "chat", fake_chat)
    monkeypatch.setattr(vanilla.vectors, "search_dense",
                        lambda c, v, k: [Hit("Doc", "body", 0.2)])
    monkeypatch.setattr(vanilla.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(vanilla.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/vanilla-rag/v1/chat/completions",
                          json={"model": "vanilla-rag",
                                "messages": [{"role": "user", "content": "q"}],
                                "temperature": 0.7, "max_tokens": 256,
                                "stream_options": {"include_usage": True},
                                "user": "owui-user"})
    assert r.status_code == 200
