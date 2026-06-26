import respx
import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.approaches import graph


@pytest.mark.asyncio
@respx.mock
async def test_graph_queries_lightrag(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_API_KEY", "k")
    respx.post("http://lightrag:9621/query").mock(
        return_value=httpx.Response(200, json={"response": "graph answer"})
    )
    app = FastAPI(); app.include_router(graph.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/graph-rag/v1/chat/completions",
                          json={"model": "graph-rag",
                                "messages": [{"role": "user", "content": "themes?"}]})
    assert r.status_code == 200
    assert "graph answer" in r.json()["choices"][0]["message"]["content"]
