"""Shared retrieve→stuff→generate step used by the text-RAG approaches."""
from __future__ import annotations

from . import litellm
from .vectors import Hit

_PROMPT = (
    "Answer the question using ONLY the context below. If the context is "
    "insufficient, say so.\n\n=== CONTEXT ===\n{context}\n\n=== QUESTION ===\n{q}"
)


def stuff(question: str, hits: list[Hit]) -> str:
    ctx = "\n\n".join(f"[{i+1}] {h.title}: {h.text}" for i, h in enumerate(hits))
    return _PROMPT.format(context=ctx, q=question)


async def answer_from_context(model: str, question: str, hits: list[Hit]) -> tuple[str, int]:
    resp = await litellm.chat(model, [{"role": "user", "content": stuff(question, hits)}])
    return resp["choices"][0]["message"]["content"], 1
