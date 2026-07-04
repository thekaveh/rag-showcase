"""Weaviate (BYO-vector) search + ingest, and TEI cross-encoder rerank.

Weaviate holds dense vectors AND a BM25 index per collection. We supply
vectors ourselves (computed via LiteLLM embeddings) so the embedding model
is identical across approaches and independent of Weaviate's module config.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)

# Single source of truth for the two collection names, shared by the approaches
# and the ingest tool (renaming a collection was previously a six-site edit).
BASE_COLLECTION = "RagBase"
CONTEXTUAL_COLLECTION = "RagContextual"


@dataclass
class Hit:
    title: str
    text: str
    score: float | None = None


def _weaviate() -> Any:
    """Open a Weaviate v4 client to the in-network instance.

    The gRPC port defaults to 50051 (Weaviate's standard) but is overridable
    via WEAVIATE_GRPC_PORT for non-standard deployments — the WEAVIATE_URL
    scheme only carries the HTTP port.
    """
    import weaviate
    from urllib.parse import urlparse

    url = urlparse(os.environ.get("WEAVIATE_URL", "http://weaviate:8080"))
    host = url.hostname or "weaviate"
    http_port = url.port or 8080
    raw_grpc = os.environ.get("WEAVIATE_GRPC_PORT", "50051")
    try:
        grpc_port = int(raw_grpc)
    except ValueError as e:
        raise ValueError(
            f"WEAVIATE_GRPC_PORT must be an integer, got {raw_grpc!r}") from e
    return weaviate.connect_to_custom(
        http_host=host, http_port=http_port, http_secure=False,
        grpc_host=host, grpc_port=grpc_port, grpc_secure=False,
    )


def ensure_collection(name: str) -> None:
    import weaviate.classes.config as wc
    client = _weaviate()
    try:
        if not client.collections.exists(name):
            client.collections.create(
                name=name,
                vectorizer_config=wc.Configure.Vectorizer.none(),
                properties=[
                    wc.Property(name="title", data_type=wc.DataType.TEXT),
                    wc.Property(name="text", data_type=wc.DataType.TEXT),
                ],
            )
    finally:
        client.close()


def delete_collection(name: str) -> None:
    """Drop a collection (and its objects) if it exists; a no-op otherwise.

    Used to make ingest idempotent: a warm re-run of start-all.sh rebuilds the
    corpus from scratch instead of appending duplicate chunks (add_chunks inserts
    with fresh UUIDs and never dedups), mirroring register's delete-then-add.
    """
    client = _weaviate()
    try:
        if client.collections.exists(name):
            client.collections.delete(name)
    finally:
        client.close()


def add_chunks(name: str, chunks: list[dict[str, Any]]) -> int:
    """chunks: [{'title','text','vector'}]. Returns count inserted."""
    client = _weaviate()
    try:
        coll = client.collections.get(name)
        with coll.batch.dynamic() as batch:
            for c in chunks:
                batch.add_object(
                    properties={"title": c["title"], "text": c["text"]},
                    vector=c["vector"],
                )
        # Weaviate v4 batches absorb per-object errors instead of raising;
        # surface them and return the count actually inserted (not the input
        # count) so callers don't over-report a partially failed ingest.
        failed = getattr(coll.batch, "failed_objects", None) or []
        if failed:
            logging.getLogger("uvicorn.error").warning(
                "add_chunks: %d/%d objects failed to insert into %r",
                len(failed), len(chunks), name)
        return len(chunks) - len(failed)
    finally:
        client.close()


def _hits_from_objects(objs: Any) -> list[Hit]:
    out: list[Hit] = []
    for o in objs:
        score = None
        if o.metadata is not None and o.metadata.score is not None:
            score = float(o.metadata.score)
        out.append(Hit(title=str(o.properties.get("title", "")),
                       text=str(o.properties.get("text", "")), score=score))
    return out


def search_dense(collection: str, query_vec: list[float], k: int) -> list[Hit]:
    client = _weaviate()
    try:
        coll = client.collections.get(collection)
        # Intentionally requests no score metadata: a pure vector search exposes
        # only distance/certainty, never the fused `score` that hybrid/BM25
        # populate, and the demo surface renders sources fine without a per-hit
        # score (see test_build_response_source_without_score). We don't request
        # metadata we don't render, so vanilla-rag's Hits carry score=None by design.
        res = coll.query.near_vector(near_vector=query_vec, limit=k)
        return _hits_from_objects(res.objects)
    finally:
        client.close()


def search_hybrid(collection: str, query: str, query_vec: list[float],
                  k: int, alpha: float = 0.5) -> list[Hit]:
    import weaviate.classes.query as wq
    client = _weaviate()
    try:
        coll = client.collections.get(collection)
        # No fusion_type → Weaviate's default relativeScoreFusion (each of BM25 +
        # dense is normalized to [0,1] and summed). alpha weights dense vs BM25.
        res = coll.query.hybrid(query=query, vector=query_vec, alpha=alpha, limit=k,
                                return_metadata=wq.MetadataQuery(score=True))
        return _hits_from_objects(res.objects)
    finally:
        client.close()


async def rerank(query: str, hits: list[Hit], top_n: int) -> list[Hit]:
    if not hits:
        return []
    endpoint = os.environ.get("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80").rstrip("/")
    try:
        max_batch = max(1, int(os.environ.get("TEI_RERANKER_MAX_BATCH", "32")))
    except ValueError:
        max_batch = 32
    ordered: list[Hit] = []
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        for start in range(0, len(hits), max_batch):
            batch = hits[start:start + max_batch]
            resp = await client.post(
                f"{endpoint}/rerank",
                json={"query": query, "texts": [h.text for h in batch]},
            )
            resp.raise_for_status()
            ranking = resp.json()
            if not isinstance(ranking, list):
                return hits[:top_n]  # unexpected reranker shape — fall back to input order
            for row in ranking:
                if not isinstance(row, dict):
                    continue  # ignore non-object rows from a misbehaving reranker
                idx = row.get("index")
                if not isinstance(idx, int) or not (0 <= idx < len(batch)):
                    continue  # ignore out-of-range indices from a misbehaving reranker
                h = batch[idx]
                ordered.append(Hit(title=h.title, text=h.text,
                                   score=float(row.get("score", 0.0))))
    # if every ranked index was out of range (or the list was empty), fall back
    # to input order rather than dropping all sources
    if not ordered:
        return hits[:top_n]
    ordered.sort(key=lambda h: h.score if h.score is not None else 0.0, reverse=True)
    return ordered[:top_n]
