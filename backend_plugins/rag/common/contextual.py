"""Anthropic-style Contextual Retrieval: a short situating blurb per chunk.

For documents longer than the context cap, the document text shown to the blurb
model is a window CENTERED on the chunk (falling back to a prefix when the chunk
isn't found verbatim) — a plain prefix cut would "situate" every chunk past the
cap against text that doesn't contain it.
"""
from __future__ import annotations

from . import config, litellm

_PROMPT = (
    "<document>\n{doc}\n</document>\n\n"
    "Here is a chunk from the document:\n<chunk>\n{chunk}\n</chunk>\n\n"
    "Give a short (1-2 sentence) context that situates this chunk within the "
    "overall document, to improve search retrieval. Answer with ONLY the context."
)

_DOC_WINDOW = 6000  # chars of document context shown to the blurb model


def _doc_window(doc_text: str, chunk_text: str) -> str:
    if len(doc_text) <= _DOC_WINDOW:
        return doc_text
    i = doc_text.find(chunk_text)
    if i == -1:
        return doc_text[:_DOC_WINDOW]
    half = max(0, (_DOC_WINDOW - len(chunk_text)) // 2)
    start = max(0, i - half)
    return doc_text[start:start + _DOC_WINDOW]


async def contextualize(doc_text: str, chunk_text: str) -> str:
    resp = await litellm.chat(
        config.role("contextual_blurb"),
        [{"role": "user", "content": _PROMPT.format(
            doc=_doc_window(doc_text, chunk_text), chunk=chunk_text)}],
    )
    choices = resp.get("choices") or []
    content = ((choices[0].get("message") or {}).get("content") if choices else None) or ""
    # Unlike pipeline.answer_from_context (whose non-string content is coerced
    # downstream by build_response), this return value goes straight into the
    # ingest batch's f"{blurb}\n\n{chunk.text}" concatenation with no such net —
    # a structured content-part list here would AttributeError on .strip() and
    # abort the whole `python -m ingest.contextual` run over one malformed reply.
    if not isinstance(content, str):
        content = ""
    return content.strip()
