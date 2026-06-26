"""Anthropic-style Contextual Retrieval: a short situating blurb per chunk."""
from __future__ import annotations

from . import config, litellm

_PROMPT = (
    "<document>\n{doc}\n</document>\n\n"
    "Here is a chunk from the document:\n<chunk>\n{chunk}\n</chunk>\n\n"
    "Give a short (1-2 sentence) context that situates this chunk within the "
    "overall document, to improve search retrieval. Answer with ONLY the context."
)


async def contextualize(doc_text: str, chunk_text: str) -> str:
    resp = await litellm.chat(
        config.role("contextual_blurb"),
        [{"role": "user", "content": _PROMPT.format(doc=doc_text[:6000], chunk=chunk_text)}],
    )
    choices = resp.get("choices") or []
    content = (choices[0].get("message", {}).get("content") if choices else None) or ""
    return content.strip()
