import json

import respx
import httpx
import pytest
from rag.common import litellm


@pytest.mark.asyncio
@respx.mock
async def test_embed_posts_to_litellm(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    route = respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
    )
    out = await litellm.embed(["hello"], model="nomic-embed-text")
    assert out == [[0.1, 0.2]]
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer sk-test"


@pytest.mark.asyncio
@respx.mock
async def test_chat_returns_json(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    route = respx.post("http://litellm:4000/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "hi", "role": "assistant"}}]
        })
    )
    out = await litellm.chat("qwen3.6", [{"role": "user", "content": "hey"}])
    assert out["choices"][0]["message"]["content"] == "hi"
    assert route.called
    assert route.calls.last.request.headers["authorization"] == "Bearer sk-test"


@pytest.mark.asyncio
@respx.mock
async def test_chat_forwards_tools_and_omits_when_absent(monkeypatch):
    # agentic-rag depends on the model actually receiving its tool schemas: chat()
    # must place `tools` in the POST body when given, and omit the key entirely when
    # not. Drop the forwarding (or send tools=None unconditionally) and agentic-rag
    # silently degrades to "answered without retrieval" while the entire agentic suite
    # — which fabricates tool_calls via a mocked chat — stays green. So assert the wire.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    route = respx.post("http://litellm:4000/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]}))
    tools = [{"type": "function", "function": {"name": "search_vectors"}}]
    await litellm.chat("m", [{"role": "user", "content": "q"}], tools=tools)
    assert json.loads(route.calls.last.request.content)["tools"] == tools
    # with no tools, the key must be absent (not present as null)
    await litellm.chat("m", [{"role": "user", "content": "q"}])
    assert "tools" not in json.loads(route.calls.last.request.content)


@pytest.mark.asyncio
@respx.mock
async def test_chat_delegates_model_request_defaults_to_litellm(monkeypatch):
    # Atlas owns per-model request defaults in its catalog (e.g. qwen3.6:latest's
    # think:false). backend_plugins/rag/common/config.py has no per-model request-
    # param function of its own (confirmed: only role()/litellm_base()/litellm_key()
    # exist) — the plugin must send only approach-level arguments (temperature) and
    # never inject an Atlas-owned knob like "think" itself.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    route = respx.post("http://litellm:4000/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={"choices": [{"message": {"content": "x"}}]}))
    await litellm.chat("qwen3.6:latest", [{"role": "user", "content": "q"}])
    body = json.loads(route.calls.last.request.content)
    assert body["temperature"] == 0.0
    assert "think" not in body


@pytest.mark.asyncio
@respx.mock
async def test_embed_uses_default_role_when_model_omitted(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    monkeypatch.setattr(litellm.config, "role", lambda r: "default-embed")
    route = respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.0]}]}))
    await litellm.embed(["x"])  # no model arg -> falls back to config.role("embed")
    assert "default-embed" in route.calls.last.request.content.decode()


@pytest.mark.asyncio
@respx.mock
async def test_embed_orders_by_index(monkeypatch):
    # /v1/embeddings may return data out of input order; embed() must restore
    # order by `index` so callers' positional zip stays correct.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [
            {"index": 1, "embedding": [1.0]},
            {"index": 0, "embedding": [0.0]},
        ]}))
    out = await litellm.embed(["a", "b"], model="nomic-embed-text")
    assert out == [[0.0], [1.0]]  # reordered by index, not raw response order


@pytest.mark.asyncio
@respx.mock
async def test_embed_raises_clear_error_on_non_json_200(monkeypatch):
    # A 200 with a non-JSON body (upstream Ollama/proxy blip) must not surface as
    # a raw JSONDecodeError, nor silently degrade to []: every caller indexes the
    # result positionally (embed([q])[0]), so a silent [] would surface as a
    # confusing downstream IndexError instead of a diagnosable failure here.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, content=b"<html>bad gateway</html>",
                                     headers={"content-type": "text/html"}))
    with pytest.raises(RuntimeError, match="malformed response"):
        await litellm.embed(["a"], model="nomic-embed-text")


@pytest.mark.asyncio
@respx.mock
async def test_embed_raises_clear_error_when_data_key_missing(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"error": "model not found"}))
    with pytest.raises(RuntimeError, match="malformed response"):
        await litellm.embed(["a"], model="nomic-embed-text")


@pytest.mark.asyncio
@respx.mock
async def test_embed_raises_clear_error_on_malformed_row(monkeypatch):
    # A "data" list with a valid shape overall but a row that isn't a
    # {"embedding": [...]} object must raise the same clear RuntimeError, not a
    # raw AttributeError/KeyError from indexing a malformed row.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": ["not-an-object"]}))
    with pytest.raises(RuntimeError, match="malformed response"):
        await litellm.embed(["a"], model="nomic-embed-text")


@pytest.mark.asyncio
@respx.mock
async def test_chat_degrades_to_empty_dict_on_non_json_200(monkeypatch, caplog):
    # a 200 with a non-JSON body must degrade to {} so callers' existing
    # `resp.get("choices") or []` fallback kicks in, instead of raising
    # JSONDecodeError and 500ing every text-generating approach. It must also
    # log a warning: the degraded content ends up as a legitimately-typed but
    # empty "" answer, which never trips build_response's non-string-answer
    # warning, so this is the only diagnostic trail for the symptom.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/chat/completions").mock(
        return_value=httpx.Response(200, content=b"<html>bad gateway</html>",
                                     headers={"content-type": "text/html"}))
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        out = await litellm.chat("m", [{"role": "user", "content": "q"}])
    assert out == {}
    assert "non-JSON" in caplog.text
    assert "'m'" in caplog.text


@pytest.mark.asyncio
@respx.mock
async def test_chat_degrades_to_empty_dict_on_non_dict_200(monkeypatch, caplog):
    # a 200 with valid JSON that isn't an object (e.g. a bare list) must also
    # degrade to {} rather than crash callers doing resp.get(...), and log a
    # warning for the same undebuggable-empty-answer reason as the non-JSON case.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/chat/completions").mock(
        return_value=httpx.Response(200, json=["unexpected", "list", "body"]))
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        out = await litellm.chat("m", [{"role": "user", "content": "q"}])
    assert out == {}
    assert "non-object" in caplog.text
    assert "'m'" in caplog.text
