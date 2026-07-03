import json
import respx
import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.approaches import graph
from rag.common import lightrag


@pytest.fixture(autouse=True)
def _clear_flavor_cache():
    # A per-test flavors.yaml override loads into the module-global cache; clear
    # before AND after so a tmp table can't leak across tests (mirrors test_flavors.py).
    graph.flavors._CACHE.clear()
    yield
    graph.flavors._CACHE.clear()

# NOTE: these tests scope respx via `with respx.mock:` inside each test body
# rather than the `@respx.mock` decorator. Several tests here mock the SAME
# LightRAG URL (/query) with different responses; the body-scoped context
# manager tears each patch down deterministically at block exit, which avoids a
# rare cross-test route-state bleed observed under pytest-asyncio's auto mode.


@pytest.mark.asyncio
async def test_graph_queries_lightrag(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_API_KEY", "k")
    with respx.mock:
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
        # the graph approach forwards the user question AND requests the graph+vector
        # "hybrid" mode — assert BOTH on the wire (rename the query key and graph-rag +
        # the agentic graph tool would send LightRAG an empty/wrong query, suite green).
        sent = json.loads(route.calls.last.request.content)
        assert sent["query"] == "themes?"
        assert sent["mode"] == "hybrid"
        assert sent["enable_rerank"] is False
        assert sent["top_k"] == 10
        assert sent["chunk_top_k"] == 5
        assert sent["max_total_tokens"] == 12000
        # auth must use X-API-Key (v1.5.4), not Authorization: Bearer
        assert route.calls.last.request.headers.get("x-api-key") == "k"
        assert "authorization" not in route.calls.last.request.headers


@pytest.mark.asyncio
async def test_graph_flavor_overrides_query_payload(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-wide
    base: graph-rag
    params:
      mode: hybrid
      top_k: 30
      chunk_top_k: 12
      max_total_tokens: 24000
      enable_rerank: false
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    with respx.mock:
        route = respx.post("http://lightrag:9621/query").mock(
            return_value=httpx.Response(200, json={"response": "wide graph answer"})
        )
        app = FastAPI(); app.include_router(graph.router)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            r = await ac.post("/graph-rag/v1/chat/completions",
                              json={"model": "graph-rag-wide",
                                    "messages": [{"role": "user", "content": "themes?"}]})
    assert r.status_code == 200
    sent = json.loads(route.calls.last.request.content)
    assert sent["mode"] == "hybrid"
    assert sent["top_k"] == 30
    assert sent["chunk_top_k"] == 12
    assert sent["max_total_tokens"] == 24000


@pytest.mark.asyncio
async def test_lightrag_upload_text_posts_to_documents_text(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    with respx.mock:
        upload = respx.post("http://lightrag:9621/documents/text").mock(
            return_value=httpx.Response(200))
        await lightrag.upload_text("My Doc", "some content")
        assert upload.called
        body = json.loads(upload.calls.last.request.content)
        assert body["text"] == "some content" and body["file_source"] == "My Doc"


@pytest.mark.asyncio
async def test_lightrag_upload_text_retries_409_backpressure(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_UPLOAD_RETRIES", "2")
    monkeypatch.setenv("LIGHTRAG_UPLOAD_RETRY_DELAY", "0")
    with respx.mock:
        upload = respx.post("http://lightrag:9621/documents/text").mock(
            side_effect=[
                httpx.Response(409, json={"status": "busy"}),
                httpx.Response(200),
            ]
        )
        await lightrag.upload_text("My Doc", "some content")
        assert upload.call_count == 2


@pytest.mark.asyncio
async def test_lightrag_query_guards_short_input(monkeypatch):
    # a <3-char query must not reach LightRAG (which 422s on min_length=3): no
    # HTTP call is attempted and a clear message is returned instead of a 500.
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    out = await lightrag.query("ok")
    assert "too short" in out


@pytest.mark.asyncio
async def test_lightrag_query_coerces_non_string_response(monkeypatch):
    # query() is annotated -> str. If LightRAG ever returns a non-string under
    # response/data, query() must coerce so every consumer is protected — notably
    # agentic-rag, which slices the raw observation (observation[:300]) and would
    # otherwise TypeError, unlike graph-rag which is shielded by build_response.
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    with respx.mock:
        respx.post("http://lightrag:9621/query").mock(
            return_value=httpx.Response(200, json={"response": {"unexpected": "object"}}))
        out = await lightrag.query("a real graph question")
        assert isinstance(out, str)
        assert "unexpected" in out


@pytest.mark.asyncio
async def test_lightrag_query_empty_answer_returns_empty_string(monkeypatch):
    # A 200 with no recognized answer field (a miss, or a response-field rename)
    # must degrade to "" — graph-rag/agentic get a clean empty string, not a
    # KeyError/None that would 500 downstream.
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    with respx.mock:
        respx.post("http://lightrag:9621/query").mock(
            return_value=httpx.Response(200, json={}))
        out = await lightrag.query("a real graph question")
        assert out == ""


@pytest.mark.asyncio
async def test_lightrag_query_reads_data_field_fallback(monkeypatch):
    # query() recognizes the answer under either `response` or `data`
    # (data.get("response") or data.get("data")). When LightRAG answers under the
    # `data` field only, query() must still return it — drop the `or data.get("data")`
    # fallback and graph-rag plus the agentic graph tool go blank, with no test
    # failing (every other test feeds `response`). So exercise the data branch.
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    with respx.mock:
        respx.post("http://lightrag:9621/query").mock(
            return_value=httpx.Response(200, json={"data": "answer via data field"}))
        out = await lightrag.query("a real graph question")
        assert out == "answer via data field"


@pytest.mark.asyncio
async def test_lightrag_query_options_are_env_overridable(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_QUERY_ENABLE_RERANK", "true")
    monkeypatch.setenv("LIGHTRAG_QUERY_TOP_K", "7")
    monkeypatch.setenv("LIGHTRAG_QUERY_CHUNK_TOP_K", "3")
    monkeypatch.setenv("LIGHTRAG_QUERY_MAX_TOTAL_TOKENS", "4096")
    with respx.mock:
        route = respx.post("http://lightrag:9621/query").mock(
            return_value=httpx.Response(200, json={"response": "ok"}))
        out = await lightrag.query("a real graph question")
        assert out == "ok"
        sent = json.loads(route.calls.last.request.content)
        assert sent["enable_rerank"] is True
        assert sent["top_k"] == 7
        assert sent["chunk_top_k"] == 3
        assert sent["max_total_tokens"] == 4096
