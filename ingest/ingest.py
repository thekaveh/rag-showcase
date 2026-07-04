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

BASE = vectors.BASE_COLLECTION
CONTEXTUAL = vectors.CONTEXTUAL_COLLECTION
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)
# Single source of truth for chunking geometry — _naive_chunks and the Docling
# request below must stay in agreement or the two chunking paths drift.
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

_log = logging.getLogger("uvicorn.error")


def _naive_chunks(path: str, name: str, size: int = CHUNK_SIZE,
                  overlap: int = CHUNK_OVERLAP) -> list[dict]:
    """Fallback chunker used when Docling is disabled/unreachable: split the
    file's text into overlapping windows. Adequate for the .md/.txt corpus."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace").strip()
    except OSError as e:
        # Degrade to "no chunks" like a genuinely empty file, but log it — otherwise
        # an unreadable corpus file is dropped from the index silently while run()
        # still counts it in `files`, hiding a real operational problem. Matches the
        # warning chunk_document() already emits when Docling is unreachable.
        _log.warning("could not read %s (%s); skipping", path, e)
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
                "chunk_size": str(CHUNK_SIZE), "chunk_overlap": str(CHUNK_OVERLAP)}
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
    docling_empty = False
    if endpoint:  # Docling enabled — prefer its structure-aware chunking
        try:
            out = await _docling_chunks(path, name, endpoint)
            if out:
                return out
            docling_empty = True  # Docling answered but produced no usable chunks
        except Exception as e:  # Docling down/misconfigured — degrade gracefully
            _log.warning("Docling unavailable (%s); attempting fallback for %s", e, name)
    if Path(path).suffix.lower() == ".pdf":
        # The naive fallback reads text; on a binary PDF that would silently embed
        # mojibake chunks. Better to drop the file loudly than index garbage — and
        # say which of the two distinct situations happened, so the operator debugs
        # the document (empty/scanned) vs the service wiring (unavailable).
        if docling_empty:
            _log.warning("Docling returned no usable chunks for %s; skipping PDF", name)
        else:
            _log.warning("no Docling available for %s; skipping PDF (naive chunking "
                         "cannot parse binary)", name)
        return []
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
    # A missing or empty corpus dir must never reach phase 2: glob() on a nonexistent
    # path silently yields nothing, and rebuilding from zero rows would drop-recreate
    # both live collections EMPTY — destroying a warm corpus on a typo'd path.
    if not files:
        raise RuntimeError(f"no ingestable documents (.txt/.md/.pdf) under {corpus_dir!r}; "
                           "refusing to rebuild collections from an empty corpus")
    # Phase 1 — do all the failure-prone work (chunk, embed, contextualize, LightRAG
    # upload) WITHOUT touching the live Weaviate collections, accumulating the rows to
    # store. A failure here leaves the existing corpus fully serveable, not half-built.
    base_rows: list[dict] = []
    ctx_rows: list[dict] = []
    for path in files:
        doc_chunks = await chunk_document(str(path))
        if not doc_chunks:
            continue
        # Prefer the pristine source text for LightRAG extraction and the
        # contextualize() window: rejoining naive chunks would duplicate every
        # CHUNK_OVERLAP span (~14% of the text) and inject paragraph breaks at
        # arbitrary offsets, skewing entity extraction. Chunk-join remains the
        # fallback for binary formats (Docling-parsed PDFs).
        if path.suffix.lower() in {".txt", ".md"}:
            try:
                doc_text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                doc_text = "\n\n".join(c["text"] for c in doc_chunks)
        else:
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
    # Same guard at the content level: files that all chunked to nothing (unreadable,
    # skipped PDFs) must not wipe the live collections either.
    if not base_rows:
        raise RuntimeError(f"no ingestable content in {len(files)} file(s) under "
                           f"{corpus_dir!r}; refusing to rebuild collections empty")
    # Phase 2 — every embedding now exists; idempotently swap each Weaviate collection
    # in a tight drop->recreate->bulk-add (mirrors register's delete-then-add).
    base_count = await _rebuild(BASE, base_rows)
    ctx_count = await _rebuild(CONTEXTUAL, ctx_rows)
    return {"files": len(files), "base_chunks": base_count, "contextual_chunks": ctx_count}


if __name__ == "__main__":
    import argparse

    # A real parser (even with a single positional) matters here: previously any
    # argument — including --help — was taken as the corpus path, and a nonexistent
    # path used to reach run() and wipe the live collections.
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Service endpoints come from env vars: DOCLING_ENDPOINT, "
               "LITELLM_BASE_URL, WEAVIATE_URL, LIGHTRAG_ENDPOINT (see README §6).")
    # Default matches start-all.sh's demo ingest. A bare "corpus" default would
    # recursively ingest the ENTIRE corpus/ tree (READMEs + every dataset union)
    # into both live collections on a no-args invocation.
    parser.add_argument("corpus_dir", nargs="?", default="corpus/raw",
                        help="directory of .txt/.md/.pdf documents (default: corpus/raw)")
    args = parser.parse_args()
    if not Path(args.corpus_dir).is_dir():
        raise SystemExit(f"corpus dir not found: {args.corpus_dir}")
    print(asyncio.run(run(args.corpus_dir)))
