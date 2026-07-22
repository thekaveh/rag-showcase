from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_contextual_enrichment_consumes_atlas_chunks_only(monkeypatch, tmp_path) -> None:
    from ingest import contextual
    from rag.common import vectors

    source = tmp_path / "graph_native" / "d.md"
    source.parent.mkdir()
    source.write_text("pristine source text", encoding="utf-8")
    chunks = [
        vectors.IngestedChunk(source="graph_native/d.md", text="chunk one", index=0),
        vectors.IngestedChunk(source="graph_native/d.md", text="chunk two", index=1),
    ]
    seen_docs: list[str] = []
    rows: list[dict] = []
    deleted: list[str] = []

    monkeypatch.setattr(vectors, "read_ingested_chunks", lambda name: chunks)

    async def fake_contextualize(document: str, chunk: str) -> str:
        seen_docs.append(document)
        return f"context for {chunk}"

    async def fake_embed(texts, model=None):
        return [[float(index)] for index, _ in enumerate(texts)]

    monkeypatch.setattr(contextual, "contextualize", fake_contextualize)
    monkeypatch.setattr(contextual.litellm, "embed", fake_embed)
    monkeypatch.setattr(vectors, "delete_collection", lambda name: deleted.append(name))
    monkeypatch.setattr(vectors, "ensure_collection", lambda name: None)
    monkeypatch.setattr(
        vectors,
        "add_chunks",
        lambda name, values: rows.extend(values) or len(values),
    )

    result = await contextual.run(
        corpus_root=str(tmp_path),
        base_collection="RagBase_graph_native",
        contextual_collection="RagContextual_graph_native",
    )

    assert result == {
        "base_collection": "RagBase_graph_native",
        "source_chunks": 2,
        "contextual_collection": "RagContextual_graph_native",
        "contextual_chunks": 2,
    }
    assert seen_docs == ["pristine source text", "pristine source text"]
    assert deleted == ["RagContextual_graph_native"]
    assert [row["title"] for row in rows] == ["graph_native/d.md", "graph_native/d.md"]
    assert [row["text"] for row in rows] == [
        "context for chunk one\n\nchunk one",
        "context for chunk two\n\nchunk two",
    ]


@pytest.mark.asyncio
async def test_contextual_enrichment_does_not_wipe_on_empty_source(monkeypatch) -> None:
    from ingest import contextual
    from rag.common import vectors

    deleted: list[str] = []
    monkeypatch.setattr(vectors, "read_ingested_chunks", lambda name: [])
    monkeypatch.setattr(vectors, "delete_collection", lambda name: deleted.append(name))

    with pytest.raises(RuntimeError, match="no Atlas-ingested chunks"):
        await contextual.run()

    assert deleted == []


@pytest.mark.asyncio
async def test_contextual_enrichment_rejects_partial_write(monkeypatch, tmp_path) -> None:
    # add_chunks returns the count actually inserted (Weaviate v4 absorbs per-
    # object errors); a partial write must surface as an error, not silently
    # leave the contextual collection with gaps that skew the comparison.
    from ingest import contextual
    from rag.common import vectors

    source = tmp_path / "g" / "d.md"
    source.parent.mkdir()
    source.write_text("doc", encoding="utf-8")
    chunks = [
        vectors.IngestedChunk(source="g/d.md", text="c1", index=0),
        vectors.IngestedChunk(source="g/d.md", text="c2", index=1),
    ]
    monkeypatch.setattr(vectors, "read_ingested_chunks", lambda name: chunks)

    async def fake_contextualize(document, chunk):
        return "ctx"

    async def fake_embed(texts, model=None):
        return [[0.0] for _ in texts]

    monkeypatch.setattr(contextual, "contextualize", fake_contextualize)
    monkeypatch.setattr(contextual.litellm, "embed", fake_embed)
    monkeypatch.setattr(vectors, "delete_collection", lambda name: None)
    monkeypatch.setattr(vectors, "ensure_collection", lambda name: None)
    monkeypatch.setattr(vectors, "add_chunks", lambda name, values: len(values) - 1)

    with pytest.raises(RuntimeError, match="partial write"):
        await contextual.run(
            corpus_root=str(tmp_path),
            base_collection="RagBase_g",
            contextual_collection="RagContextual_g",
        )
