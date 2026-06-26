import respx
import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.approaches import n8n


@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_forwards_and_wraps(monkeypatch):
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json={"answer": "routed answer", "route": "complex"})
    )
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "hard q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "routed answer" in content and "complex" in content  # route surfaced
