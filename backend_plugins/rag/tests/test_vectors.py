import respx
import httpx
import pytest
from rag.common.vectors import rerank, Hit


@pytest.mark.asyncio
@respx.mock
async def test_rerank_reorders_by_tei_score(monkeypatch):
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    hits = [Hit("A", "alpha", 0.1), Hit("B", "bravo", 0.2), Hit("C", "charlie", 0.3)]
    # TEI says index 2 is best, then 0, then 1
    respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json=[
            {"index": 2, "score": 0.99},
            {"index": 0, "score": 0.50},
            {"index": 1, "score": 0.10},
        ])
    )
    out = await rerank("q", hits, top_n=2)
    assert [h.title for h in out] == ["C", "A"]
    assert out[0].score == 0.99
