import pytest
from rag.common import contextual


@pytest.mark.asyncio
async def test_contextualize_calls_blurb_model(monkeypatch):
    seen = {}
    async def fake_chat(model, messages, **kw):
        seen["model"] = model
        seen["prompt"] = messages[-1]["content"]
        return {"choices": [{"message": {"content": "This chunk is about X."}}]}
    monkeypatch.setattr(contextual.litellm, "chat", fake_chat)
    monkeypatch.setattr(contextual.config, "role", lambda r: "gemma4:31b")
    out = await contextual.contextualize("FULL DOC", "CHUNK")
    assert out == "This chunk is about X."
    assert seen["model"] == "gemma4:31b"
    assert "FULL DOC" in seen["prompt"] and "CHUNK" in seen["prompt"]
