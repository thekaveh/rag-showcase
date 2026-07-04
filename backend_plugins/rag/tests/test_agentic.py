import json
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.common import flavors
from rag.approaches import agentic


@pytest.fixture(autouse=True)
def _clear_flavor_cache():
    # Some agentic tests load a per-test flavors.yaml into the module-global
    # flavors._CACHE; clear before AND after so a test's tmp table can never leak
    # into another test's ordering (mirrors test_flavors.py's fixture).
    flavors._CACHE.clear()
    yield
    flavors._CACHE.clear()


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
    seen = {}
    def fake_search(c, q, v, k):
        seen["collection"] = c; seen["q"] = q
        return [Hit("D", "alpha body", 0.5)]
    monkeypatch.setattr(agentic.vectors, "search_hybrid", fake_search)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "final answer" in content
    assert seen["collection"] == "RagBase"  # search_vectors retrieves from the base index
    # the model-chosen tool query (extracted via json.loads + args.get + type-coercion,
    # NOT a trivial req.last_user() pass-through) must reach retrieval — rename the key
    # at agentic._run_tool and every real tool call searches on "", with the suite green.
    assert seen["q"] == "alpha"
    assert "Action" in content and "search_vectors" in content  # trace surfaced
    assert len(turns) == 2
    # cost footer counts the tool's work too: 2 chat turns + 1 search_vectors embed
    # = 3, matching the +1=embed convention of vanilla/hybrid (not just chat turns).
    assert "3 LLM calls" in content


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
    seen = {}
    async def fake_graph(q, mode="hybrid"): seen["q"] = q; return "GRAPH-OBS-XYZ"
    def fake_role(r): seen["role"] = r; return "qwen3.6"
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.lightrag, "query", fake_graph)
    monkeypatch.setattr(agentic.config, "role", fake_role)

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
    # cost footer counts the delegated graph call too: 2 chat turns + 1 query_graph = 3
    # (sibling of the search_vectors "+1"; change query_graph's +1 to 0 and this drops to 2).
    assert "3 LLM calls" in content
    assert seen["role"] == "agentic"  # the agent uses the "agentic" role (wrong key misroutes)
    assert seen["q"] == "themes"      # the extracted tool query reaches the graph backend


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
async def test_agentic_flavor_overrides_max_steps_and_vector_top_k(tmp_path, monkeypatch):
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: agentic-rag-deeper
    base: agentic-rag
    params:
      max_steps: 6
      vector_top_k: 8
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(f))
    turns = []
    calls = {}
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "alpha"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_search(c, q, v, k):
        calls["top_k"] = k
        return [Hit("D", "alpha body", 0.5)]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid", fake_search)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag-deeper",
                                "messages": [{"role": "user", "content": "q"}]})

    assert r.status_code == 200
    assert calls["top_k"] == 8
    assert len(turns) == 2


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


@pytest.mark.parametrize("bad_args", ["null", "5", '"hi"', "[1, 2]", "true", "{bad"])
@pytest.mark.asyncio
async def test_agentic_tolerates_non_object_tool_args(monkeypatch, bad_args):
    # tool-call arguments that are valid JSON but NOT an object (null/number/
    # string/array/bool), or not JSON at all ("{bad"), must be coerced to {} —
    # not crash args.get(...)/json.loads -> 500.
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


@pytest.mark.asyncio
async def test_agentic_flavor_max_steps_actually_bounds_the_loop(tmp_path, monkeypatch):
    # A tool-EVERY-turn model with a max_steps:2 flavor must stop after exactly 2
    # LLM turns with the exhaustion message. (The other flavor test's model answers
    # on turn 2, so it never observes the max_steps plumb — this one does.)
    manifest = tmp_path / "flavors.yaml"
    manifest.write_text(
        "flavors:\n"
        "  - alias: agentic-rag-two\n"
        "    base: agentic-rag\n"
        "    params:\n"
        "      max_steps: 2\n",
        encoding="utf-8")
    monkeypatch.setenv("RAG_FLAVORS_FILE", str(manifest))
    flavors._CACHE.clear()
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
                          json={"model": "agentic-rag-two",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    assert "MAX_STEPS" in r.json()["choices"][0]["message"]["content"]
    assert len(turns) == 2  # the flavor override, not the module default of 4


@pytest.mark.asyncio
async def test_agentic_handles_parallel_tool_calls_in_one_turn(monkeypatch):
    # Local models do emit multiple tool_calls in a single assistant turn. Both
    # must run, both observations must be traced, the turn's thought must render
    # exactly once, and each tool reply must link its own call id.
    turns = []
    tool_msgs = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": "I will use both tools.",
                "tool_calls": [
                    {"id": "cv", "type": "function",
                     "function": {"name": "search_vectors",
                                  "arguments": json.dumps({"query": "alpha"})}},
                    {"id": "cg", "type": "function",
                     "function": {"name": "query_graph",
                                  "arguments": json.dumps({"query": "beta graph"})}},
                ]}}]}
        tool_msgs.extend(m for m in messages if m.get("role") == "tool")
        return {"choices": [{"message": {"role": "assistant", "content": "done"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    async def fake_graph(q, mode="hybrid", options=None): return "GRAPH-OBS"
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.lightrag, "query", fake_graph)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "VEC-OBS body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "VEC-OBS" in content and "GRAPH-OBS" in content  # both observations traced
    assert content.count("I will use both tools.") == 1     # thought rendered once
    # one tool reply per call, ids linked to the assistant turn's call ids
    assert [m["tool_call_id"] for m in tool_msgs] == ["cv", "cg"]
    # 2 chat turns + 1 embed (search_vectors) + 1 delegated graph call = 4
    assert "4 LLM calls" in content


@pytest.mark.asyncio
async def test_agentic_tool_failure_becomes_observation_not_500(monkeypatch):
    # A tool-side outage (Weaviate/embed/LightRAG down) must not abort the episode
    # as a bare 500 — it becomes an observation the model can react to.
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(1)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "alpha"})}}]}}]}
        # the model sees the failure observation and still answers
        assert any(m.get("role") == "tool" and "failed" in m.get("content", "")
                   for m in messages)
        return {"choices": [{"message": {"role": "assistant", "content": "recovered"}}]}
    async def broken_embed(texts, model=None):
        raise RuntimeError("embedding backend down")
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", broken_embed)
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")
    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "recovered" in content
    assert "failed: RuntimeError" in content  # trace surfaces the failure
