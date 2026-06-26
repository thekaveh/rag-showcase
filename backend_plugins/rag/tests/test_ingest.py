import respx
import httpx
import pytest
import ingest.ingest as ing


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_calls_docling(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    doc = tmp_path / "a.txt"
    doc.write_text("hello world")
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
    uploads = []

    async def fake_chunk(path): return [{"title": "t", "text": "chunk"}]
    async def fake_embed(texts, model=None): return [[0.0] for _ in texts]
    async def fake_contextualize(doc, chunk): return "blurb"
    async def fake_upload(title, text): uploads.append(title)
    def fake_ensure(name): pass
    def fake_add(name, rows): added[name] += len(rows); return len(rows)

    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", fake_embed)
    monkeypatch.setattr(ing, "contextualize", fake_contextualize)
    monkeypatch.setattr(ing.lightrag, "upload_text", fake_upload)
    monkeypatch.setattr(ing.vectors, "ensure_collection", fake_ensure)
    monkeypatch.setattr(ing.vectors, "add_chunks", fake_add)

    result = await ing.run(str(tmp_path))
    assert result == {"files": 2, "base_chunks": 2, "contextual_chunks": 2}
    assert added == {"RagBase": 2, "RagContextual": 2}
    assert len(uploads) == 2  # one LightRAG upload per file


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
async def test_run_raises_on_embedding_count_mismatch(monkeypatch, tmp_path):
    (tmp_path / "d.txt").write_text("doc", encoding="utf-8")
    async def fake_chunk(path): return [{"title": "t", "text": "c1"},
                                        {"title": "t", "text": "c2"}]
    async def short_embed(texts, model=None): return [[0.0]]  # fewer than inputs
    monkeypatch.setattr(ing, "chunk_document", fake_chunk)
    monkeypatch.setattr(ing.litellm, "embed", short_embed)
    monkeypatch.setattr(ing.vectors, "ensure_collection", lambda n: None)
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    import pytest as _pytest
    with _pytest.raises(RuntimeError, match="embedding count mismatch"):
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
    monkeypatch.setattr(ing.vectors, "add_chunks", lambda n, r: len(r))
    monkeypatch.setattr(ing.lightrag, "upload_text", lambda t, x: None)
    import pytest as _pytest
    with _pytest.raises(RuntimeError, match="contextual embedding count mismatch"):
        await ing.run(str(tmp_path))
