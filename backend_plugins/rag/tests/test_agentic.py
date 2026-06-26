import json
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import agentic


@pytest.mark.asyncio
async def test_agentic_runs_tool_then_answers(monkeypatch):
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(messages)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "alpha"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "alpha body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "final answer" in content
    assert "Action" in content and "search_vectors" in content  # trace surfaced
    assert len(turns) == 2
