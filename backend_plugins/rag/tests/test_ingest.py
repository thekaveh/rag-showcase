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
