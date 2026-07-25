from __future__ import annotations

from pathlib import Path

import pytest

import ingest.contextual as ic
from rag.common.vectors import IngestedChunk


def test_document_text_reads_the_source_file_for_md_and_txt(tmp_path: Path) -> None:
    (tmp_path / "doc.md").write_text("full document body", encoding="utf-8")
    chunks = [IngestedChunk(source="doc.md", text="a chunk", index=0)]
    assert ic._document_text(tmp_path, "doc.md", chunks) == "full document body"


def test_document_text_falls_back_to_joined_chunks_for_other_extensions(tmp_path: Path) -> None:
    (tmp_path / "doc.pdf").write_bytes(b"%PDF-not-real-text")
    chunks = [
        IngestedChunk(source="doc.pdf", text="chunk one", index=0),
        IngestedChunk(source="doc.pdf", text="chunk two", index=1),
    ]
    assert ic._document_text(tmp_path, "doc.pdf", chunks) == "chunk one\n\nchunk two"


def test_document_text_falls_back_when_source_escapes_corpus_root(tmp_path: Path) -> None:
    # A source path that resolves outside corpus_root (e.g. "../../etc/passwd" from
    # a corrupted Atlas chunk record) must not be read — fall back to chunk text.
    outside = tmp_path.parent / "outside.md"
    outside.write_text("should never be read", encoding="utf-8")
    corpus_root = tmp_path / "corpus"
    corpus_root.mkdir()
    chunks = [IngestedChunk(source="../outside.md", text="safe chunk", index=0)]
    assert ic._document_text(corpus_root, "../outside.md", chunks) == "safe chunk"


def test_document_text_falls_back_on_read_failure(tmp_path: Path, monkeypatch) -> None:
    doc = tmp_path / "doc.md"
    doc.write_text("body", encoding="utf-8")
    chunks = [IngestedChunk(source="doc.md", text="chunk fallback", index=0)]

    def raising_read_text(self, *args, **kwargs):
        raise OSError("simulated disk read failure")

    monkeypatch.setattr(Path, "read_text", raising_read_text)
    assert ic._document_text(tmp_path, "doc.md", chunks) == "chunk fallback"


@pytest.mark.asyncio
async def test_run_raises_on_embedding_count_mismatch(monkeypatch) -> None:
    chunks = [IngestedChunk(source="a.md", text="chunk text", index=0)]
    monkeypatch.setattr(ic.vectors, "read_ingested_chunks", lambda collection: chunks)
    monkeypatch.setattr(ic, "_document_text", lambda root, source, chunks: "doc")

    async def fake_contextualize(document, chunk_text):
        return "blurb"

    async def fake_embed(texts):
        return []  # mismatched: one row in, zero vectors out

    monkeypatch.setattr(ic, "contextualize", fake_contextualize)
    monkeypatch.setattr(ic.litellm, "embed", fake_embed)

    with pytest.raises(RuntimeError, match="embedding count mismatch"):
        await ic.run(corpus_root="/does/not/matter")
