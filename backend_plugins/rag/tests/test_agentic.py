import json
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import agentic


@pytest.mark.asyncio
async def test_agentic_runs_tool_then_answers(monkeypatch):
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(messages)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "alpha"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "alpha body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "final answer" in content
    assert "Action" in content and "search_vectors" in content  # trace surfaced
    assert len(turns) == 2


@pytest.mark.asyncio
async def test_agentic_surfaces_thought_in_trace(monkeypatch):
    # when the model emits reasoning (content) ALONGSIDE a tool call, the ReAct trace
    # must surface it as "**Thought:** ...". Every other agentic test sends content=None
    # on the tool turn, so agentic.py's thought branch is otherwise unexercised — break
    # it and the agent's reasoning silently vanishes from the trace, all tests green.
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(messages)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant",
                "content": "I should search the corpus first.",
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "alpha"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "alpha body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "**Thought:** I should search the corpus first." in content


@pytest.mark.asyncio
async def test_agentic_uses_query_graph_tool(monkeypatch):
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(messages)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "g1", "type": "function",
                  "function": {"name": "query_graph",
                               "arguments": json.dumps({"query": "themes"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "graph-based answer"}}]}
    async def fake_graph(q, mode="hybrid"): return "GRAPH-OBS-XYZ"
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.lightrag, "query", fake_graph)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "graph-based answer" in content
    assert "query_graph" in content and "GRAPH-OBS-XYZ" in content
    assert len(turns) == 2


@pytest.mark.asyncio
async def test_agentic_tolerates_malformed_tool_call(monkeypatch):
    # a tool call missing function.name / id must not raise; it gets answered
    # with an "unknown tool" observation and the loop proceeds to a final answer.
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(messages)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": None, "type": "function", "function": {}}]}}]}  # null id, no name
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "done" in r.json()["choices"][0]["message"]["content"]
    assert len(turns) == 2


@pytest.mark.asyncio
async def test_agentic_stops_and_reports_at_max_steps(monkeypatch):
    # a model that calls a tool every turn must terminate at MAX_STEPS with the
    # fallback message, having made exactly MAX_STEPS LLM calls (no runaway loop).
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        return {"choices": [{"message": {"role": "assistant", "content": None,
            "tool_calls": [{"id": f"c{len(turns)}", "type": "function",
              "function": {"name": "search_vectors",
                           "arguments": json.dumps({"query": "x"})}}]}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "MAX_STEPS" in r.json()["choices"][0]["message"]["content"]
    assert len(turns) == agentic.MAX_STEPS  # exactly MAX_STEPS LLM calls, then stop


@pytest.mark.asyncio
async def test_agentic_links_synthesized_id_for_null_id_tool_call(monkeypatch):
    # a null-id tool call must get a synthesized id that the tool reply mirrors,
    # so the re-sent assistant+tool pair satisfies the OpenAI contract next turn.
    turns = []
    captured: list = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": None, "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "a"})}}]}}]}
        captured.extend(messages)  # the re-sent assistant+tool pair from turn 1
        return {"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assistant = next(m for m in captured
                     if m.get("role") == "assistant" and m.get("tool_calls"))
    tool = next(m for m in captured if m.get("role") == "tool")
    synth = assistant["tool_calls"][0]["id"]
    assert synth, "a null tool-call id must be replaced with a non-empty id"
    assert tool["tool_call_id"] == synth  # reply is linked to the assistant call


@pytest.mark.asyncio
async def test_agentic_empty_final_content_is_not_max_steps(monkeypatch):
    # an empty-but-valid final response (no tool calls, content="") must NOT be
    # relabeled as the MAX_STEPS exhaustion message.
    async def fake_chat(model, messages, tools=None, **kw):
        return {"choices": [{"message": {"role": "assistant", "content": ""}}]}
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "MAX_STEPS" not in content  # empty answer, not the exhaustion fallback


@pytest.mark.asyncio
async def test_agentic_tolerates_choice_without_message(monkeypatch):
    # a 2xx whose first choice lacks a "message" key must degrade (empty answer),
    # like the other approaches — not raise KeyError into a 500.
    async def fake_chat(model, messages, tools=None, **kw):
        return {"choices": [{}]}
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200  # graceful degrade, not a 500


@pytest.mark.asyncio
async def test_agentic_empty_choices_degrades(monkeypatch):
    # a structurally-valid 2xx with an EMPTY choices list (a content-filter / no-
    # completion turn) must degrade to "(no response from model)", not IndexError
    # on choices[0] -> 500. The agentic-loop sibling of the pipeline/contextual
    # {"choices": []} degrades (agentic.py:70-73), otherwise unexercised.
    async def fake_chat(model, messages, tools=None, **kw):
        return {"choices": []}
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "(no response from model)" in r.json()["choices"][0]["message"]["content"]


@pytest.mark.parametrize("bad_args", ["null", "5", '"hi"', "[1, 2]", "true"])
@pytest.mark.asyncio
async def test_agentic_tolerates_non_object_tool_args(monkeypatch, bad_args):
    # tool-call arguments that are valid JSON but NOT an object (null/number/
    # string/array/bool) must be coerced to {} — not crash args.get(...) -> 500.
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors", "arguments": bad_args}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200  # coerced to {}, no AttributeError


@pytest.mark.parametrize("bad_query", [5, [1, 2], {"x": 1}, None, True])
@pytest.mark.asyncio
async def test_agentic_tolerates_non_string_query_value(monkeypatch, bad_query):
    # a tool-arg dict whose `query` VALUE is not a string must degrade to empty,
    # not crash (e.g. lightrag.query(5).strip() -> AttributeError -> 500). Uses the
    # real lightrag.query so its short-query guard short-circuits without HTTP.
    import json as _json
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "query_graph",
                               "arguments": _json.dumps({"query": bad_query})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200  # non-string query coerced to "", degrades cleanly
