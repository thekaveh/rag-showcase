import respx
import httpx
import pytest
import register.register_models as reg


@pytest.mark.asyncio
@respx.mock
async def test_register_deletes_existing_then_adds(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [
            {"model_name": "vanilla-rag", "model_info": {"id": "old-1"}}]}))
    delete = respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(200, json={}))
    new = respx.post("http://litellm:4000/model/new").mock(
        return_value=httpx.Response(200, json={}))
    await reg.run()
    assert delete.called                       # removed the stale vanilla-rag
    assert new.call_count == len(reg.MODELS)   # added all six
    body = new.calls[0].request.read().decode()
    assert "backend:8000" in body and "openai/" in body
