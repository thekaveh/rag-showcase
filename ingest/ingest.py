"""Corpus ingestion: Docling -> chunks -> Weaviate(base+contextual) + LightRAG."""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

import httpx

# Make the plugin package importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend_plugins"))

from rag.common import litellm, vectors
from rag.common.contextual import contextualize
from rag.common import lightrag

BASE = "RagBase"
CONTEXTUAL = "RagContextual"
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


def _naive_chunks(path: str, name: str, size: int = 800, overlap: int = 100) -> list[dict]:
    """Fallback chunker used when Docling is disabled/unreachable: split the
    file's text into overlapping windows. Adequate for the .md/.txt corpus."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError as e:
        # Degrade to "no chunks" like a genuinely empty file, but log it — otherwise
        # an unreadable corpus file is dropped from the index silently while run()
        # still counts it in `files`, hiding a real operational problem. Matches the
        # warning chunk_document() already emits when Docling is unreachable.
        logging.getLogger("uvicorn.error").warning(
            "could not read %s (%s); skipping", path, e)
        return []
    out: list[dict] = []
    step = max(1, size - overlap)
    for i in range(0, len(text), step):
        piece = text[i:i + size].strip()
        if piece:
            out.append({"title": name, "text": piece})
    return out


async def _docling_chunks(path: str, name: str, endpoint: str) -> list[dict]:
    with open(path, "rb") as fh:
        files = {"file": (name, fh, "application/octet-stream")}
        data = {"output_format": "markdown", "enable_chunking": "true",
                "chunk_size": "800", "chunk_overlap": "100"}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{endpoint}/v1/document/convert",
                                     files=files, data=data)
            resp.raise_for_status()
            payload = resp.json()
    out = []
    for ch in payload.get("chunks", []):
        text = ch.get("text") or ""
        if not text:
            continue  # skip chunks Docling returned without text
        section = (ch.get("metadata") or {}).get("section_title") or ""
        title = f"{name} — {section}" if section else name
        out.append({"title": title, "text": text})
    return out


async def chunk_document(path: str) -> list[dict]:
    """Chunk a document, preferring Docling when it's configured, else naive."""
    name = Path(path).name
    endpoint = os.environ.get("DOCLING_ENDPOINT", "").rstrip("/")
    if endpoint:  # Docling enabled — prefer its structure-aware chunking
        try:
            out = await _docling_chunks(path, name, endpoint)
            if out:
                return out
        except Exception as e:  # Docling down/misconfigured — degrade gracefully
            logging.getLogger("uvicorn.error").warning(
                "Docling unavailable (%s); naive-chunking %s", e, name)
    return _naive_chunks(path, name)


async def _rebuild(name: str, rows: list[dict]) -> int:
    """Idempotently replace a collection: drop, recreate, then bulk-add ``rows``.

    The destructive drop runs only once the replacement rows are already in hand
    (computed in run()'s phase 1), so a failure during the long embed phase never
    leaves a warm corpus empty, and the rebuild window stays the seconds it takes to
    bulk-insert (no LLM calls between the drop and the add). Mirrors register's
    delete-then-add idempotency.
    """
    await asyncio.to_thread(vectors.delete_collection, name)
    await asyncio.to_thread(vectors.ensure_collection, name)
    if not rows:
        return 0
    return await asyncio.to_thread(vectors.add_chunks, name, rows)


async def run(corpus_dir: str) -> dict:
    files = sorted(p for p in Path(corpus_dir).glob("**/*")
                   if p.is_file() and p.suffix.lower() in {".txt", ".md", ".pdf"})
    # Phase 1 — do all the failure-prone work (chunk, embed, contextualize, LightRAG
    # upload) WITHOUT touching the live Weaviate collections, accumulating the rows to
    # store. A failure here leaves the existing corpus fully serveable, not half-built.
    base_rows: list[dict] = []
    ctx_rows: list[dict] = []
    for path in files:
        doc_chunks = await chunk_document(str(path))
        if not doc_chunks:
            continue
        doc_text = "\n\n".join(c["text"] for c in doc_chunks)
        # Base collection rows
        vecs = await litellm.embed([c["text"] for c in doc_chunks])
        if len(vecs) != len(doc_chunks):
            raise RuntimeError(f"embedding count mismatch for {path.name}: "
                               f"{len(vecs)} vectors for {len(doc_chunks)} chunks")
        base_rows.extend({**c, "vector": v} for c, v in zip(doc_chunks, vecs))
        # Contextual collection rows (blurb-prefixed)
        rows = []
        for c in doc_chunks:
            blurb = await contextualize(doc_text, c["text"])
            rows.append({"title": c["title"], "text": f"{blurb}\n\n{c['text']}"})
        ctx_vecs = await litellm.embed([r["text"] for r in rows])
        if len(ctx_vecs) != len(rows):
            raise RuntimeError(f"contextual embedding count mismatch for {path.name}: "
                               f"{len(ctx_vecs)} vectors for {len(rows)} chunks")
        ctx_rows.extend({**r, "vector": v} for r, v in zip(rows, ctx_vecs))
        # LightRAG builds its own KG and dedups by content hash, so uploading here
        # (before the swap) is safe and idempotent across re-runs.
        await lightrag.upload_text(path.name, doc_text)
    # Phase 2 — every embedding now exists; idempotently swap each Weaviate collection
    # in a tight drop->recreate->bulk-add (mirrors register's delete-then-add).
    base_count = await _rebuild(BASE, base_rows)
    ctx_count = await _rebuild(CONTEXTUAL, ctx_rows)
    return {"files": len(files), "base_chunks": base_count, "contextual_chunks": ctx_count}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "corpus"
    print(asyncio.run(run(target)))
