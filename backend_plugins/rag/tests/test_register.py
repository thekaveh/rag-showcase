import json

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
    # decode EVERY /model/new payload (not just calls[0]) and assert the full set —
    # call_count alone would pass a bug that registers MODELS[0] six times.
    payloads = [json.loads(c.request.read().decode()) for c in new.calls]
    # (a) each approach registers under its OWN name, as an openai/ provider whose
    #     api_base is its OWN distinct backend route (not all pointing at one path)
    assert sorted(p["model_name"] for p in payloads) == sorted(m["model_name"] for m in reg.MODELS)
    assert all(p["litellm_params"]["model"].startswith("openai/") for p in payloads)
    assert all("backend:8000" in p["litellm_params"]["api_base"] for p in payloads)
    assert len({p["litellm_params"]["api_base"] for p in payloads}) == len(reg.MODELS)
    # (b) the api_key (read from env at run-time) is merged into litellm_params —
    #     drop the merge and all six register keyless, so every routed call fails
    assert all(p["litellm_params"]["api_key"] == "sk-master" for p in payloads)


@pytest.mark.asyncio
@respx.mock
async def test_register_skips_delete_when_clean(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": []}))
    delete = respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(200, json={}))
    new = respx.post("http://litellm:4000/model/new").mock(
        return_value=httpx.Response(200, json={}))
    await reg.run()
    assert not delete.called                       # nothing to remove on a clean slate
    assert new.call_count == len(reg.MODELS)       # still registers all six


@pytest.mark.asyncio
@respx.mock
async def test_register_uses_api_key_when_master_absent(monkeypatch):
    # in-container the master key is exposed as LITELLM_API_KEY, not _MASTER_KEY
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.delenv("LITELLM_MASTER_KEY", raising=False)
    monkeypatch.setenv("LITELLM_API_KEY", "sk-fromapi")
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": []}))
    new = respx.post("http://litellm:4000/model/new").mock(
        return_value=httpx.Response(200, json={}))
    await reg.run()
    assert new.calls.last.request.headers["authorization"] == "Bearer sk-fromapi"


@pytest.mark.asyncio
@respx.mock
async def test_register_deletes_only_its_own_models(monkeypatch):
    # the delete guard (`if model_name in ours`) protects a SHARED LiteLLM gateway:
    # foreign operator/user models must survive a showcase (re)registration. Drop
    # the guard and every backend startup wipes unrelated models — this pins it.
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [
            {"model_name": "vanilla-rag", "model_info": {"id": "ours-1"}},
            {"model_name": "user-private-gpt", "model_info": {"id": "keep-1"}}]}))
    delete = respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(200, json={}))
    respx.post("http://litellm:4000/model/new").mock(
        return_value=httpx.Response(200, json={}))
    await reg.run()
    deleted_ids = [json.loads(c.request.read().decode())["id"] for c in delete.calls]
    assert "ours-1" in deleted_ids        # our stale row was removed
    assert "keep-1" not in deleted_ids    # the foreign model was left untouched
