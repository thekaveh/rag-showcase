"""Corpus ingestion: Docling -> chunks -> Weaviate(base+contextual) + LightRAG."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Make the plugin package importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend_plugins"))

from rag.common import litellm, vectors  # noqa: E402
from rag.common.contextual import contextualize  # noqa: E402
from rag.common import lightrag  # noqa: E402

BASE = "RagBase"
CONTEXTUAL = "RagContextual"
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


async def chunk_document(path: str) -> list[dict]:
    endpoint = os.environ.get("DOCLING_ENDPOINT", "http://docling-gpu:8000").rstrip("/")
    name = Path(path).name
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


async def run(corpus_dir: str) -> dict:
    await asyncio.to_thread(vectors.ensure_collection, BASE)
    await asyncio.to_thread(vectors.ensure_collection, CONTEXTUAL)
    files = sorted(p for p in Path(corpus_dir).glob("**/*")
                   if p.is_file() and p.suffix.lower() in {".txt", ".md", ".pdf"})
    base_count = ctx_count = 0
    for path in files:
        doc_chunks = await chunk_document(str(path))
        if not doc_chunks:
            continue
        doc_text = "\n\n".join(c["text"] for c in doc_chunks)
        # Base collection
        vecs = await litellm.embed([c["text"] for c in doc_chunks])
        if len(vecs) != len(doc_chunks):
            raise RuntimeError(f"embedding count mismatch for {path.name}: "
                               f"{len(vecs)} vectors for {len(doc_chunks)} chunks")
        base_count += await asyncio.to_thread(vectors.add_chunks, BASE, [
            {**c, "vector": v} for c, v in zip(doc_chunks, vecs)])
        # Contextual collection (blurb-prefixed)
        ctx_rows = []
        for c in doc_chunks:
            blurb = await contextualize(doc_text, c["text"])
            ctx_rows.append({"title": c["title"], "text": f"{blurb}\n\n{c['text']}"})
        ctx_vecs = await litellm.embed([r["text"] for r in ctx_rows])
        if len(ctx_vecs) != len(ctx_rows):
            raise RuntimeError(f"contextual embedding count mismatch for {path.name}: "
                               f"{len(ctx_vecs)} vectors for {len(ctx_rows)} chunks")
        ctx_count += await asyncio.to_thread(vectors.add_chunks, CONTEXTUAL, [
            {**r, "vector": v} for r, v in zip(ctx_rows, ctx_vecs)])
        # LightRAG (builds its own KG)
        await lightrag.upload_text(path.name, doc_text)
    return {"files": len(files), "base_chunks": base_count, "contextual_chunks": ctx_count}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "corpus"
    print(asyncio.run(run(target)))
