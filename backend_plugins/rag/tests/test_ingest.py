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
    deleted = []
    monkeypatch.setattr(ing.litellm, "embed", short_embed)
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: deleted.append(n))
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    with pytest.raises(RuntimeError, match="embedding count mismatch"):
        await ing.run(str(tmp_path))
    # atomicity: the embed failure happens in phase 1, BEFORE the destructive swap,
    # so the live Weaviate collections are never dropped — a failed re-run leaves the
    # warm corpus fully intact instead of half-rebuilt (the regression this guards).
    assert deleted == []


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
    async def fake_upload(t, x): return None
    monkeypatch.setattr(ing.lightrag, "upload_text", fake_upload)
    with pytest.raises(RuntimeError, match="contextual embedding count mismatch"):
        await ing.run(str(tmp_path))


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_falls_back_when_docling_errors(monkeypatch, tmp_path, caplog):
    # Docling configured but unreachable -> graceful degrade to naive chunking
    # (the exception path, distinct from the DOCLING_ENDPOINT-unset path).
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    doc = tmp_path / "d.md"
    doc.write_text("# T\n\n" + ("y" * 900), encoding="utf-8")
    respx.post("http://docling-gpu:8000/v1/document/convert").mock(
        side_effect=httpx.ConnectError("docling down"))
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        chunks = await ing.chunk_document(str(doc))
    assert len(chunks) >= 1
    assert all(c["title"] == "d.md" and c["text"] for c in chunks)  # naive chunks
    # pin the exception-path wording: it must say the fallback is being ATTEMPTED
    # (for a PDF the fallback then still skips), not promise naive chunking.
    assert "attempting fallback" in caplog.text


def test_naive_chunks_logs_and_skips_unreadable_file(tmp_path, caplog):
    # An unreadable corpus file degrades to "no chunks" (like a genuinely empty file)
    # but MUST log a warning — otherwise run() drops it from the index while still
    # counting it in `files`, hiding the failure. Mirrors the Docling-unreachable log.
    missing = tmp_path / "nope.md"  # never created -> OSError on read
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        out = ing._naive_chunks(str(missing), "nope.md")
    assert out == []
    assert "could not read" in caplog.text


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


@pytest.mark.asyncio
async def test_run_refuses_missing_or_empty_corpus_dir(monkeypatch, tmp_path):
    # glob() on a nonexistent path yields nothing without error; run() must refuse to
    # reach the destructive phase-2 swap rather than rebuild both collections empty
    # (the "typo'd path wipes a warm demo corpus" regression).
    deleted = []
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: deleted.append(n))
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    with pytest.raises(RuntimeError, match="no ingestable documents"):
        await ing.run(str(tmp_path / "typo-subdir"))     # nonexistent path
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(RuntimeError, match="no ingestable documents"):
        await ing.run(str(empty))                        # exists but holds no documents
    assert deleted == []  # the swap was never reached


@pytest.mark.asyncio
async def test_run_refuses_when_all_files_chunk_to_nothing(monkeypatch, tmp_path):
    # Files exist but none yields content (unreadable files, skipped PDFs): still
    # refuse the swap — rebuilding from zero rows would wipe the live collections.
    (tmp_path / "a.txt").write_text("", encoding="utf-8")
    deleted = []
    async def no_chunks(path): return []
    monkeypatch.setattr(ing, "chunk_document", no_chunks)
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: deleted.append(n))
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    with pytest.raises(RuntimeError, match="no ingestable content"):
        await ing.run(str(tmp_path))
    assert deleted == []


@pytest.mark.asyncio
async def test_chunk_document_skips_pdf_when_docling_unavailable(monkeypatch, tmp_path, caplog):
    # Without Docling, the naive fallback must not read a binary PDF as text — that
    # would silently embed mojibake chunks. The file is dropped with a warning.
    monkeypatch.delenv("DOCLING_ENDPOINT", raising=False)
    pdf = tmp_path / "doc.pdf"
    pdf.write_bytes(b"%PDF-1.4 \x00\x01binary")
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        chunks = await ing.chunk_document(str(pdf))
    assert chunks == []
    assert "skipping PDF" in caplog.text
    # the unavailable-skip wording specifically — not the empty-chunks message,
    # which shares the "skipping PDF" substring.
    assert "no Docling available" in caplog.text


@pytest.mark.asyncio
async def test_run_feeds_pristine_source_text_to_lightrag_and_contextualize(monkeypatch, tmp_path):
    # For .txt/.md the ORIGINAL file text must reach LightRAG extraction and the
    # contextualize window — a chunk-join would duplicate every overlap span and
    # inject paragraph breaks at arbitrary offsets. (Chunk-join remains the
    # fallback for binary formats only.)
    source = "first paragraph of the pristine document.\n\nsecond paragraph."
    (tmp_path / "d.md").write_text(source, encoding="utf-8")
    uploads, ctx_docs = [], []
    async def fake_chunk(path):
        return [{"title": "t", "text": "CHUNK-A"}, {"title": "t", "text": "CHUNK-B"}]
    async def fake_embed(texts, model=None): return [[0.0] for _ in texts]
    async def fake_ctx(doc, chunk):
        ctx_docs.append(doc)
        return "blurb"
    async def fake_upload(title, text): uploads.append(text)
    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", fake_embed)
    monkeypatch.setattr(ing, "contextualize", fake_ctx)
    monkeypatch.setattr(ing.lightrag, "upload_text", fake_upload)
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "delete_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))

    await ing.run(str(tmp_path))

    assert uploads == [source]                     # pristine text, not "CHUNK-A\n\nCHUNK-B"
    assert all(doc == source for doc in ctx_docs)  # contextualize sees the same


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_pdf_skip_names_docling_empty_result(monkeypatch, tmp_path, caplog):
    # Docling answered 200 but yielded no usable chunks (e.g. a scanned PDF): the
    # skip warning must point the operator at the DOCUMENT, not the service wiring.
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    pdf = tmp_path / "scan.pdf"
    pdf.write_bytes(b"%PDF-1.4 \x00")
    respx.post("http://docling-gpu:8000/v1/document/convert").mock(
        return_value=httpx.Response(200, json={"chunks": []}))
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        chunks = await ing.chunk_document(str(pdf))
    assert chunks == []
    assert "returned no usable chunks" in caplog.text
    assert "no Docling available" not in caplog.text
