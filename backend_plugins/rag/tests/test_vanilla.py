import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import vanilla


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
