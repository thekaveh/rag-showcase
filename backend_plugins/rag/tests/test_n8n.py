import json

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
    route = respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
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
    # forwarding the user query to the workflow IS the wrapper's whole job — assert the
    # wire payload, not just the mock's return. Change the key or stop forwarding and the
    # workflow gets an empty/wrong query and answers garbage, with this test still green.
    assert json.loads(route.calls.last.request.content) == {"query": "hard q"}


@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_falls_back_on_missing_keys(monkeypatch):
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json={}))  # neither answer nor route
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "unknown" in r.json()["choices"][0]["message"]["content"]  # route fallback


@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_tolerates_null_answer(monkeypatch):
    # {"answer": null} must not crash (None + str TypeError in build_response)
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json={"answer": None, "route": None}))
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "unknown" in r.json()["choices"][0]["message"]["content"]


@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_unwraps_list_body(monkeypatch):
    # an operator-built "Respond With: All Incoming Items" node returns a JSON
    # array; the wrapper must use the first object item, not 500 on list.get().
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json=[{"answer": "from list", "route": "simple"}]))
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "from list" in r.json()["choices"][0]["message"]["content"]


@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_skips_non_dict_items_in_list(monkeypatch):
    # an "All Incoming Items" array can carry a null/non-dict FIRST item; the wrapper
    # must skip to the first DICT (next(d for d in data if isinstance(d, dict))), not
    # blindly take data[0]. Simplify to `data[0] if data else {}` and this body 500s
    # on None.get — while the existing dict-first and empty-list tests stay green.
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json=[None, {"answer": "second item", "route": "simple"}]))
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "second item" in r.json()["choices"][0]["message"]["content"]


@pytest.mark.parametrize("body", [[], "oops", 5])
@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_degrades_on_non_object_body(monkeypatch, body):
    # empty array / bare scalar body must degrade to the route fallback, not raise
    # AttributeError -> 500. (A JSON null hits the same non-dict branch.)
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json=body))
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "unknown" in r.json()["choices"][0]["message"]["content"]
