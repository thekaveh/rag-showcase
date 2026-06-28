import respx
import httpx
import pytest
import ingest.ingest as ing


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_calls_docling(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    doc = tmp_path / "a.txt"
    doc.write_text("hello world", encoding="utf-8")
    respx.post("http://docling-gpu:8000/v1/document/convert").mock(
        return_value=httpx.Response(200, json={
            "chunks": [{"text": "hello world",
                        "metadata": {"chunk_index": 0, "section_title": "Intro"}}]
        })
    )
    chunks = await ing.chunk_document(str(doc))
    assert chunks[0]["text"] == "hello world"
    assert chunks[0]["title"].endswith("Intro") or "a.txt" in chunks[0]["title"]


@pytest.mark.asyncio
async def test_run_populates_all_three_indexes(monkeypatch, tmp_path):
    (tmp_path / "d1.txt").write_text("doc one", encoding="utf-8")
    (tmp_path / "d2.txt").write_text("doc two", encoding="utf-8")
    added = {"RagBase": 0, "RagContextual": 0}
    rows_by_name = {"RagBase": [], "RagContextual": []}
    uploads = []

    async def fake_chunk(path): return [{"title": "t", "text": "chunk"}]
    async def fake_embed(texts, model=None): return [[0.0] for _ in texts]
    async def fake_contextualize(doc, chunk): return "blurb"
    async def fake_upload(title, text): uploads.append(title)
    deleted = []
    def fake_ensure(name): pass
    def fake_delete(name): deleted.append(name)
    def fake_add(name, rows):
        rows_by_name[name].extend(rows); added[name] += len(rows); return len(rows)

    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", fake_embed)
    monkeypatch.setattr(ing, "contextualize", fake_contextualize)
    monkeypatch.setattr(ing.lightrag, "upload_text", fake_upload)
    monkeypatch.setattr(ing.vectors, "ensure_collection", fake_ensure)
    monkeypatch.setattr(ing.vectors, "delete_collection", fake_delete)
    monkeypatch.setattr(ing.vectors, "add_chunks", fake_add)

    result = await ing.run(str(tmp_path))
    assert result == {"files": 2, "base_chunks": 2, "contextual_chunks": 2}
    assert added == {"RagBase": 2, "RagContextual": 2}
    assert len(uploads) == 2  # one LightRAG upload per file
    # contextual-rag's distinguishing transform: each RagContextual row is the
    # per-chunk blurb prepended to the chunk text, while RagBase carries the bare
    # chunk. Drop that prefix (ingest.py:98) and contextual-rag silently collapses
    # into hybrid-rag with every other test still green — so assert it explicitly.
    assert all(r["text"] == "blurb\n\nchunk" for r in rows_by_name["RagContextual"])
    assert all(r["text"] == "chunk" for r in rows_by_name["RagBase"])
    # idempotent build: BOTH Weaviate collections are dropped (then recreated)
    # before ingest, so a warm re-run rebuilds the corpus instead of duplicating it.
    assert deleted == ["RagBase", "RagContextual"]


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_skips_textless_chunks(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    doc = tmp_path / "a.txt"; doc.write_text("x", encoding="utf-8")
    respx.post("http://docling-gpu:8000/v1/document/convert").mock(
        return_value=httpx.Response(200, json={"chunks": [
            {"metadata": {"section_title": "Empty"}},   # no text key
            {"text": "real", "metadata": {}}]}))
    chunks = await ing.chunk_document(str(doc))
    assert [c["text"] for c in chunks] == ["real"]


@pytest.mark.asyncio
async def test_chunk_document_naive_fallback_when_docling_disabled(monkeypatch, tmp_path):
    # DOCLING_ENDPOINT unset (doc-processor disabled) -> naive text chunking
    monkeypatch.delenv("DOCLING_ENDPOINT", raising=False)
    doc = tmp_path / "d.md"
    doc.write_text("# Title\n\n" + ("x" * 1000), encoding="utf-8")
    chunks = await ing.chunk_document(str(doc))
    assert len(chunks) >= 2  # ~1000 chars split into overlapping ~800-char windows
    assert all(c["title"] == "d.md" and c["text"] for c in chunks)


@pytest.mark.asyncio
async def test_run_raises_on_embedding_count_mismatch(monkeypatch, tmp_path):
    (tmp_path / "d.txt").write_text("doc", encoding="utf-8")
    async def fake_chunk(path): return [{"title": "t", "text": "c1"},
                                        {"title": "t", "text": "c2"}]
    async def short_embed(texts, model=None): return [[0.0]]  # fewer than inputs
    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", short_embed)
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    with pytest.raises(RuntimeError, match="embedding count mismatch"):
        await ing.run(str(tmp_path))


@pytest.mark.asyncio
async def test_run_raises_on_contextual_embedding_mismatch(monkeypatch, tmp_path):
    (tmp_path / "d.txt").write_text("doc", encoding="utf-8")
    async def fake_chunk(path): return [{"title": "t", "text": "c1"},
                                        {"title": "t", "text": "c2"}]
    calls = {"n": 0}
    async def embed(texts, model=None):
        calls["n"] += 1
        # base embed (call 1) returns the right count; contextual embed (call 2) is short
        return [[0.0]] * len(texts) if calls["n"] == 1 else [[0.0]]
    async def fake_ctx(doc, chunk): return "blurb"
    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", embed)
    monkeypatch.setattr(ing, "contextualize", fake_ctx)
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    monkeypatch.setattr(ing.lightrag, "upload_text", lambda t, x: None)
    with pytest.raises(RuntimeError, match="contextual embedding count mismatch"):
        await ing.run(str(tmp_path))


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_falls_back_when_docling_errors(monkeypatch, tmp_path):
    # Docling configured but unreachable -> graceful degrade to naive chunking
    # (the exception path, distinct from the DOCLING_ENDPOINT-unset path).
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    doc = tmp_path / "d.md"
    doc.write_text("# T\n\n" + ("y" * 900), encoding="utf-8")
    respx.post("http://docling-gpu:8000/v1/document/convert").mock(
        side_effect=httpx.ConnectError("docling down"))
    chunks = await ing.chunk_document(str(doc))
    assert len(chunks) >= 1
    assert all(c["title"] == "d.md" and c["text"] for c in chunks)  # naive chunks


@pytest.mark.asyncio
async def test_run_skips_files_yielding_no_chunks(monkeypatch, tmp_path):
    # a file that produces no chunks (e.g. a textless PDF) is skipped, never
    # embedded or uploaded; the files count still reflects all globbed files.
    (tmp_path / "good.txt").write_text("good", encoding="utf-8")
    (tmp_path / "empty.txt").write_text("", encoding="utf-8")
    embedded, uploads = [], []
    async def fake_chunk(path):
        return [] if path.endswith("empty.txt") else [{"title": "t", "text": "c"}]
    async def fake_embed(texts, model=None):
        embedded.append(list(texts)); return [[0.0] for _ in texts]
    async def fake_ctx(doc, chunk): return "blurb"
    async def fake_upload(t, x): uploads.append(t)
    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", fake_embed)
    monkeypatch.setattr(ing, "contextualize", fake_ctx)
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    monkeypatch.setattr(ing.lightrag, "upload_text", fake_upload)
    result = await ing.run(str(tmp_path))
    assert result == {"files": 2, "base_chunks": 1, "contextual_chunks": 1}
    assert uploads == ["good.txt"]            # empty file never uploaded
    assert all(len(t) > 0 for t in embedded)  # embed never called with []
