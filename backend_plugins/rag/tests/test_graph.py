import json
import respx
import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.approaches import graph
from rag.common import lightrag


@pytest.mark.asyncio
@respx.mock
async def test_graph_queries_lightrag(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_API_KEY", "k")
    route = respx.post("http://lightrag:9621/query").mock(
        return_value=httpx.Response(200, json={"response": "graph answer"})
    )
    app = FastAPI(); app.include_router(graph.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/graph-rag/v1/chat/completions",
                          json={"model": "graph-rag",
                                "messages": [{"role": "user", "content": "themes?"}]})
    assert r.status_code == 200
    assert "graph answer" in r.json()["choices"][0]["message"]["content"]
    # the graph approach must request the graph+vector "hybrid" mode
    assert json.loads(route.calls.last.request.content)["mode"] == "hybrid"
    # auth must use X-API-Key (v1.5.0), not Authorization: Bearer
    assert route.calls.last.request.headers.get("x-api-key") == "k"
    assert "authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
@respx.mock
async def test_lightrag_upload_text_posts_to_documents_text(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    upload = respx.post("http://lightrag:9621/documents/text").mock(
        return_value=httpx.Response(200))
    await lightrag.upload_text("My Doc", "some content")
    assert upload.called
    body = json.loads(upload.calls.last.request.content)
    assert body["text"] == "some content" and body["file_source"] == "My Doc"


@pytest.mark.asyncio
async def test_lightrag_query_guards_short_input(monkeypatch):
    # a <3-char query must not reach LightRAG (which 422s on min_length=3): no
    # HTTP call is attempted and a clear message is returned instead of a 500.
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    out = await lightrag.query("ok")
    assert "too short" in out
