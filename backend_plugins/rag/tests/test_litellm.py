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
