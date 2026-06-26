"""OpenAI-compatible request/response shaping + uniform 'why' surfacing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    # `model`, `stream`, and `temperature` are accepted for OpenAI-compat (so
    # OpenWebUI's payloads validate) but intentionally NOT honored: every
    # approach generates at temperature 0 for a fair side-by-side comparison,
    # and responses are returned whole (clients that send stream=true fall back
    # to the non-streamed body). Only `messages` (via last_user) drives behavior.
    model: str
    messages: list[dict[str, Any]]
    stream: bool = False
    temperature: float | None = None

    def last_user(self) -> str:
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
        return ""


@dataclass
class Source:
    title: str
    snippet: str
    score: float | None = None


@dataclass
class Metrics:
    seconds: float
    chunks: int
    llm_calls: int
    cloud_calls: int


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _render_sources(sources: list[Source]) -> str:
    if not sources:
        return ""
    lines = ["\n\n<details><summary>🔎 Retrieved context "
             f"({_plural(len(sources), 'source')})</summary>\n"]
    for i, s in enumerate(sources, 1):
        score = f" · score {s.score:.3f}" if s.score is not None else ""
        lines.append(f"\n**{i}. {s.title}**{score}\n\n> {s.snippet}\n")
    lines.append("\n</details>")
    return "".join(lines)


def _render_footer(m: Metrics) -> str:
    return (f"\n\n---\n📊 {m.seconds:.1f}s · {_plural(m.chunks, 'chunk')} · "
            f"{_plural(m.llm_calls, 'LLM call')} · {m.cloud_calls} cloud")


def build_response(model: str, answer: str, sources: list[Source],
                   metrics: Metrics) -> dict[str, Any]:
    # `answer` is the choke point for every approach. Coerce a non-string answer
    # (e.g. an operator-built n8n workflow that returns a non-string, or a backend
    # that returns structured/list content) to "" so the concatenation below can't
    # raise `list/dict + str` -> 500; sources + metrics still render.
    if not isinstance(answer, str):
        answer = ""
    content = answer + _render_sources(sources) + _render_footer(metrics)
    return {
        "id": f"ragshow-{model}",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
