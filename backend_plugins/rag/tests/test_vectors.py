import json

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
    route = respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json=[
            {"index": 2, "score": 0.99},
            {"index": 0, "score": 0.50},
            {"index": 1, "score": 0.10},
        ])
    )
    out = await rerank("q", hits, top_n=2)
    assert [h.title for h in out] == ["C", "A"]
    assert out[0].score == 0.99
    # also pin the request payload: the cross-encoder must score the chunk BODIES
    # (not titles) against the query. Send `h.title` instead and ranking silently
    # degrades in prod while this test — which only checked the mock's fabricated
    # ordering — stays green. So assert what actually goes on the wire.
    sent = json.loads(route.calls.last.request.content)
    assert sent["query"] == "q"
    assert sent["texts"] == ["alpha", "bravo", "charlie"]


@pytest.mark.asyncio
@respx.mock
async def test_rerank_splits_batches_over_tei_client_limit(monkeypatch):
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    monkeypatch.setenv("TEI_RERANKER_MAX_BATCH", "32")
    hits = [Hit(f"H{i}", f"text {i}", 0.0) for i in range(40)]
    route = respx.post("http://tei-reranker:80/rerank").mock(
        side_effect=[
            httpx.Response(200, json=[
                {"index": 31, "score": 0.50},
                {"index": 0, "score": 0.10},
            ]),
            httpx.Response(200, json=[
                {"index": 7, "score": 0.99},
            ]),
        ])

    out = await rerank("q", hits, top_n=3)

    assert [h.title for h in out] == ["H39", "H31", "H0"]
    assert len(route.calls) == 2
    first = json.loads(route.calls[0].request.content)
    second = json.loads(route.calls[1].request.content)
    assert len(first["texts"]) == 32
    assert len(second["texts"]) == 8


@pytest.mark.asyncio
async def test_rerank_empty_hits_short_circuits():
    # early-return guard: no TEI call is made, so no HTTP mock is needed
    assert await rerank("q", [], top_n=5) == []


@pytest.mark.asyncio
@respx.mock
async def test_rerank_falls_back_on_non_list_response(monkeypatch):
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    hits = [Hit("A", "a", 0.1), Hit("B", "b", 0.2)]
    respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json={"detail": "unexpected"}))
    out = await rerank("q", hits, top_n=1)
    assert out == hits[:1]  # unexpected shape -> input order, no TypeError


@pytest.mark.asyncio
@respx.mock
async def test_rerank_falls_back_when_all_indices_out_of_range(monkeypatch):
    # a misbehaving reranker returning only out-of-range indices must not drop
    # every source; rerank falls back to input order instead of returning [].
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    hits = [Hit("A", "a", 0.1), Hit("B", "b", 0.2)]
    respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json=[{"index": 99, "score": 0.9}]))
    out = await rerank("q", hits, top_n=2)
    assert out == hits[:2]  # not dropped to []


class _FakeBatchCtx:
    """Stand-in for the `coll.batch.dynamic()` context manager."""
    def __init__(self, parent):
        self._parent = parent
    def __enter__(self):
        return self
    def __exit__(self, *exc):
        return False
    def add_object(self, properties, vector):
        self._parent.added.append((properties, vector))


class _FakeBatch:
    def __init__(self, failed):
        self.added = []
        self.failed_objects = failed
    def dynamic(self):
        return _FakeBatchCtx(self)


class _FakeCollection:
    def __init__(self, failed):
        self.batch = _FakeBatch(failed)


class _FakeWeaviateClient:
    def __init__(self, failed):
        self._coll = _FakeCollection(failed)
        self.closed = False
    @property
    def collections(self):
        coll = self._coll
        class _Collections:
            def get(self, name):
                return coll
        return _Collections()
    def close(self):
        self.closed = True


def _chunks(n):
    return [{"title": f"t{i}", "text": f"x{i}", "vector": [float(i)]} for i in range(n)]


def test_add_chunks_returns_full_count_when_none_fail(monkeypatch):
    from rag.common import vectors
    client = _FakeWeaviateClient(failed=[])
    monkeypatch.setattr(vectors, "_weaviate", lambda: client)
    n = vectors.add_chunks("RagBase", _chunks(3))
    assert n == 3                          # all inserted
    assert len(client._coll.batch.added) == 3
    # assert the property MAPPING, not just the count: title->title, text->text,
    # and the vector passed through. Swap the mapping (e.g. title<->text) and the
    # count stays 3 while Weaviate stores bodies in the title field — corrupting
    # BM25 and the Source(title, text) display for every text-RAG approach — with
    # no test failing. So pin the exact (properties, vector) tuples.
    assert client._coll.batch.added[0] == ({"title": "t0", "text": "x0"}, [0.0])
    assert client._coll.batch.added[2] == ({"title": "t2", "text": "x2"}, [2.0])
    assert client.closed is True           # client always closed (finally)


def test_add_chunks_subtracts_failed_objects_and_warns(monkeypatch, caplog):
    import logging
    from rag.common import vectors
    client = _FakeWeaviateClient(failed=[object()])  # one per-object failure
    monkeypatch.setattr(vectors, "_weaviate", lambda: client)
    with caplog.at_level(logging.WARNING, logger="uvicorn.error"):
        n = vectors.add_chunks("RagBase", _chunks(3))
    assert n == 2                          # 3 attempted − 1 failed = 2 actually inserted
    assert any("failed to insert" in r.getMessage() for r in caplog.records)
    assert client.closed is True


class _FakeColls:
    def __init__(self, present): self.present = present; self.deleted = []
    def exists(self, name): return self.present
    def delete(self, name): self.deleted.append(name)


class _FakeDelClient:
    def __init__(self, present): self.collections = _FakeColls(present); self.closed = False
    def close(self): self.closed = True


def test_delete_collection_drops_when_present(monkeypatch):
    # ingest idempotency: an existing collection is dropped so a warm re-run
    # rebuilds it instead of appending duplicate chunks.
    from rag.common import vectors
    client = _FakeDelClient(present=True)
    monkeypatch.setattr(vectors, "_weaviate", lambda: client)
    vectors.delete_collection("RagBase")
    assert client.collections.deleted == ["RagBase"]
    assert client.closed is True            # client always closed (finally)


def test_delete_collection_noop_when_absent(monkeypatch):
    # first-ever run: nothing exists yet, so delete must be a no-op (never error),
    # and still close the client.
    from rag.common import vectors
    client = _FakeDelClient(present=False)
    monkeypatch.setattr(vectors, "_weaviate", lambda: client)
    vectors.delete_collection("RagBase")
    assert client.collections.deleted == []
    assert client.closed is True
