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
import time

from fastapi import APIRouter

from ..common import config, litellm, lightrag, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response

router = APIRouter()
COLLECTION = "RagBase"
MAX_STEPS = 4

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


async def _run_tool(name: str, args: dict) -> str:
    q = args.get("query", "")
    if name == "search_vectors":
        vec = (await litellm.embed([q]))[0]
        hits = await asyncio.to_thread(vectors.search_hybrid, COLLECTION, q, vec, 5)
        return "\n".join(f"- {h.title}: {h.text[:200]}" for h in hits) or "(no results)"
    if name == "query_graph":
        return await lightrag.query(q, mode="hybrid")
    return f"(unknown tool {name})"


@router.post("/agentic-rag/v1/chat/completions")
async def agentic_rag(req: ChatRequest):
    t0 = time.monotonic()
    model = config.role("agentic")
    messages = [{"role": "system", "content": _SYSTEM},
                {"role": "user", "content": req.last_user()}]
    trace: list[str] = []
    llm_calls = 0
    answer = ""
    for _ in range(MAX_STEPS):
        resp = await litellm.chat(model, messages, tools=_TOOLS)
        llm_calls += 1
        choices = resp.get("choices") or []
        if not choices:
            answer = "(no response from model)"
            break
        msg = choices[0]["message"]
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            answer = msg.get("content") or ""
            break
        messages.append(msg)
        thought = (msg.get("content") or "").strip()
        for call in tool_calls:
            # defensive against malformed tool calls from local models: a
            # missing name flows to _run_tool, which returns an "unknown tool"
            # observation, so the tool_call still gets a response (no dangling
            # call left for the next turn).
            fn = call.get("function") or {}
            name = fn.get("name") or ""
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            observation = await _run_tool(name, args)
            step = ""
            if thought:
                step += f"**Thought:** {thought}\n\n"
                thought = ""  # show the turn's reasoning once
            step += (f"**Action:** `{name}({args.get('query','')})`\n\n"
                     f"**Observation:** {observation[:300]}")
            trace.append(step)
            messages.append({"role": "tool", "tool_call_id": call.get("id") or "",
                             "content": observation})
    if not answer:
        answer = "(agent reached MAX_STEPS without producing a final answer)"
    trace_md = "\n\n".join(f"**Step {i+1}.** {t}" for i, t in enumerate(trace)) \
        or "(answered without retrieval)"
    sources = [Source("🤖 Agent trace", trace_md, None)]
    metrics = Metrics(time.monotonic() - t0, len(trace), llm_calls, 0)
    return build_response("agentic-rag", answer, sources, metrics)
