"""agentic-rag: a ReAct loop that decides when/what to retrieve.

Tools (corpus-scoped for fair comparison):
  - search_vectors(query): hybrid retrieval over the base collection
  - query_graph(query): LightRAG graph+vector answer
The loop runs up to MAX_STEPS, surfaces each tool step as a trace, then
returns the model's final answer.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time

from fastapi import APIRouter

from ..common import config, litellm, lightrag, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, resolve_flavor, respond

router = APIRouter()
COLLECTION = vectors.BASE_COLLECTION
MAX_STEPS = 4
_log = logging.getLogger("uvicorn.error")

_TOOLS = [
    {"type": "function", "function": {
        "name": "search_vectors",
        "description": "Hybrid keyword+semantic search over the document corpus.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "query_graph",
        "description": "Ask the knowledge graph a thematic or multi-hop question.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
]

_SYSTEM = ("You are a research agent. Use the tools to gather evidence before "
           "answering. Call a tool when you need information; otherwise answer.")


async def _run_tool(name: str, args: dict, params: dict) -> tuple[str, int]:
    """Run a tool. Returns (observation, llm_calls) where llm_calls counts the
    LiteLLM/LLM work the tool did — the query embedding for search_vectors, the
    delegated graph generation for query_graph — so agentic-rag's footer counts
    cost the same way the other approaches do (vanilla/hybrid: +1 = embed;
    graph-rag: +1 = the delegated call). An unknown tool does no such work."""
    raw = args.get("query")
    q = raw if isinstance(raw, str) else ""  # non-string query (malformed) -> empty
    if name == "search_vectors":
        if not q.strip():
            # Mirror query_graph's short-query guard (lightrag enforces min length
            # server-side): don't embed + search the empty string.
            return "(no results — empty search query)", 0
        vec = (await litellm.embed([q]))[0]
        top_k = int(params.get("vector_top_k", 5))
        hits = await asyncio.to_thread(vectors.search_hybrid, COLLECTION, q, vec, top_k)
        obs = "\n".join(f"- {h.title}: {h.text[:200]}" for h in hits) or "(no results)"
        return obs, 1  # +1 = the query embedding
    if name == "query_graph":
        if len(q.strip()) < 3:
            # Mirror lightrag.query's short-query guard locally: it would return
            # this same message having done NO delegated LLM work, so billing +1
            # would over-report the pinned cost footer (search_vectors' empty-query
            # 0 is the sibling; malformed args coerce to "" above and land here).
            return "(query too short for the knowledge graph)", 0
        mode = str(params.get("graph_mode", "hybrid"))
        return await lightrag.query(q, mode=mode), 1  # +1 = delegated graph call
    return f"(unknown tool {name})", 0


@router.post("/agentic-rag/v1/chat/completions")
async def agentic_rag(req: ChatRequest):
    t0 = time.monotonic()
    flavor = resolve_flavor(req, "agentic-rag")
    params = flavor.params
    max_steps = int(params.get("max_steps", MAX_STEPS))
    model = config.role("agentic")
    messages = [{"role": "system", "content": _SYSTEM},
                {"role": "user", "content": req.last_user()}]
    trace: list[str] = []
    llm_calls = 0
    answer = None
    for step_i in range(max_steps):
        resp = await litellm.chat(model, messages, tools=_TOOLS)
        llm_calls += 1
        # We harden against malformed VALUES the local model controls (content,
        # and each tool call's id/name/arguments — handled below), but trust the
        # OpenAI response STRUCTURE that the LiteLLM gateway enforces (choices is a
        # list of objects; message/tool_calls/function are objects). A structurally
        # malformed envelope is a gateway-contract violation, handled like any 5xx.
        choices = resp.get("choices") or []
        if not choices:
            answer = "(no response from model)"
            break
        msg = choices[0].get("message") or {}  # degrade like the other approaches
        # a non-string content (some backends return structured content blocks)
        # would break .strip()/answer concatenation, so coerce to str once.
        raw_content = msg.get("content")
        content = raw_content if isinstance(raw_content, str) else ""
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            answer = content
            break
        messages.append(msg)
        thought = content.strip()
        for j, call in enumerate(tool_calls):
            # Local models sometimes emit a tool call with a null/absent id. The
            # OpenAI contract requires each tool reply's tool_call_id to match an
            # id in the preceding assistant message, so synthesize a stable one
            # when missing — mutating `call`, which aliases the just-appended
            # msg's tool_calls — so a later turn that re-sends this pair can't
            # 400 at the gateway on an id mismatch.
            if not call.get("id"):
                call["id"] = f"call_{step_i}_{j}"
            # defensive against malformed tool calls from local models: a
            # missing name flows to _run_tool, which returns an "unknown tool"
            # observation, so the tool_call still gets a response (no dangling
            # call left for the next turn).
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            if not isinstance(args, dict):  # valid JSON but not an object
                args = {}                   # (null/number/string/array/bool)
            try:
                observation, tool_llm_calls = await _run_tool(name, args, params)
            except Exception as e:
                # A failed tool (Weaviate down, embed failure, LightRAG 5xx) must
                # not abort the whole multi-step episode as a bare 500 — feed the
                # failure back as an observation the model can react to (standard
                # ReAct practice). Broad catch is deliberate: this loop is the
                # resilience boundary and the log carries the specifics.
                _log.warning("agentic tool %s failed: %s: %s",
                             name, type(e).__name__, e)
                observation, tool_llm_calls = f"(tool {name} failed: {type(e).__name__})", 0
            llm_calls += tool_llm_calls  # count the tool's embed / delegated call too
            step = ""
            if thought:
                step += f"**Thought:** {thought}\n\n"
                thought = ""  # show the turn's reasoning once
            step += (f"**Action:** `{name}({args.get('query','')})`\n\n"
                     f"**Observation:** {observation[:300]}")
            trace.append(step)
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": observation})
    if answer is None:  # loop exhausted on tool calls; "" is a valid empty answer
        answer = "(agent reached MAX_STEPS without producing a final answer)"
    trace_md = "\n\n".join(f"**Step {i+1}.** {t}" for i, t in enumerate(trace)) \
        or "(answered without retrieval)"
    sources = [Source("🤖 Agent trace", trace_md, None)]
    # chunks=0: the agent retrieves via tools (shown in the trace), not as a
    # flat stuffed-chunk count — consistent with the other delegating
    # approaches (graph-rag, n8n-adaptive-rag).
    metrics = Metrics(time.monotonic() - t0, 0, llm_calls, 0)
    return respond(req, flavor.alias, answer, sources, metrics)
