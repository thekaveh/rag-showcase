import json

import respx
import httpx
import pytest
from rag.common import vectors
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


@pytest.mark.asyncio
@respx.mock
async def test_rerank_tolerates_null_score(monkeypatch):
    # a present-but-null score ("score": null) must not raise TypeError on
    # float(None); the row keeps its place, sorted as 0.0 like an unscored hit.
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    hits = [Hit("A", "a"), Hit("B", "b")]
    respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json=[{"index": 0, "score": None},
                                               {"index": 1, "score": 0.9}]))
    out = await rerank("q", hits, top_n=2)
    assert [h.title for h in out] == ["B", "A"]  # B (0.9) ranks above A (null -> 0.0)
    assert out[1].score is None  # null-score row retained, not dropped or 500


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


class _Obj:
    """Stand-in for a Weaviate query result object (properties + metadata.score)."""
    def __init__(self, title, text, score=None):
        self.properties = {"title": title, "text": text}
        self.metadata = type("M", (), {"score": score})() if score is not None else None


def test_hits_from_objects_maps_properties_and_score():
    hits = vectors._hits_from_objects([
        _Obj("A", "alpha", 0.75),
        _Obj("B", "beta"),                       # no metadata at all -> score None
    ])
    assert hits[0] == vectors.Hit("A", "alpha", 0.75)
    assert hits[1] == vectors.Hit("B", "beta", None)


def test_hits_from_objects_tolerates_metadata_without_score():
    class _NoScoreMeta:
        score = None
    obj = _Obj("C", "gamma")
    obj.metadata = _NoScoreMeta()
    assert vectors._hits_from_objects([obj]) == [vectors.Hit("C", "gamma", None)]


def test_hits_from_objects_accepts_atlas_ingestion_properties():
    obj = _Obj("ignored", "ignored", 0.8)
    obj.properties = {
        "source": "graph_native/d.md",
        "content": "Atlas-owned plain chunk",
        "profile": "graph_native",
        "chunkIndex": 3,
    }

    assert vectors._hits_from_objects([obj]) == [
        vectors.Hit("graph_native/d.md", "Atlas-owned plain chunk", 0.8)
    ]


def test_read_ingested_chunks_preserves_source_order_and_closes(monkeypatch):
    seen = {"closed": False}

    class _Stored:
        def __init__(self, source, content, index):
            self.properties = {
                "source": source,
                "content": content,
                "chunkIndex": index,
            }

    class _Collection:
        def iterator(self):
            return iter([
                _Stored("b.md", "b1", 1),
                _Stored("a.md", "a0", 0),
                _Stored("b.md", "b0", 0),
            ])

    class _Client:
        @property
        def collections(self):
            class _Collections:
                def get(self, name):
                    assert name == "RagBase_graph_native"
                    return _Collection()

            return _Collections()

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(vectors, "_weaviate", _Client)

    assert vectors.read_ingested_chunks("RagBase_graph_native") == [
        vectors.IngestedChunk("a.md", "a0", 0),
        vectors.IngestedChunk("b.md", "b0", 0),
        vectors.IngestedChunk("b.md", "b1", 1),
    ]
    assert seen["closed"] is True


def _fake_query_client(seen):
    """Fake Weaviate client capturing near_vector/hybrid kwargs (search-path twin
    of _FakeWeaviateClient, which covers the batch-insert path)."""
    class _Res:
        objects = [_Obj("T", "txt", 0.5)]

    class _Query:
        def near_vector(self, near_vector, limit):
            seen["near_vector"] = (near_vector, limit)
            return _Res()
        def hybrid(self, query, vector, alpha, limit, return_metadata):
            seen["hybrid"] = (query, vector, alpha, limit)
            seen["metadata_requested"] = return_metadata is not None
            return _Res()

    class _Coll:
        query = _Query()

    class _Client:
        closed = False
        @property
        def collections(self):
            class _Collections:
                def get(self, name):
                    seen["collection"] = name
                    return _Coll()
            return _Collections()
        def close(self):
            seen["closed"] = True

    return _Client()


def test_search_dense_passes_vector_and_k_and_closes(monkeypatch):
    seen = {}
    monkeypatch.setattr(vectors, "_weaviate", lambda: _fake_query_client(seen))
    hits = vectors.search_dense("RagBase", [0.1, 0.2], 7)
    assert seen["collection"] == "RagBase"
    assert seen["near_vector"] == ([0.1, 0.2], 7)   # k reaches Weaviate's limit
    assert seen["closed"] is True                    # client closed even on success
    assert hits == [vectors.Hit("T", "txt", 0.5)]


def test_search_hybrid_passes_alpha_k_and_requests_score(monkeypatch):
    import sys
    import types
    # search_hybrid imports weaviate.classes.query lazily (the dev env deliberately
    # omits weaviate-client); stub the module chain with real ModuleType instances
    # so the dotted import resolves.
    weaviate_mod = types.ModuleType("weaviate")
    classes_mod = types.ModuleType("weaviate.classes")
    query_mod = types.ModuleType("weaviate.classes.query")
    query_mod.MetadataQuery = lambda score: ("MetadataQuery", score)
    weaviate_mod.classes = classes_mod
    classes_mod.query = query_mod
    monkeypatch.setitem(sys.modules, "weaviate", weaviate_mod)
    monkeypatch.setitem(sys.modules, "weaviate.classes", classes_mod)
    monkeypatch.setitem(sys.modules, "weaviate.classes.query", query_mod)
    seen = {}
    monkeypatch.setattr(vectors, "_weaviate", lambda: _fake_query_client(seen))
    hits = vectors.search_hybrid("RagBase", "find alpha", [0.3], 12, alpha=0.25)
    assert seen["hybrid"] == ("find alpha", [0.3], 0.25, 12)  # BM25 text + dense both plumbed
    assert seen["metadata_requested"] is True  # hybrid DOES request the fused score
    assert seen["closed"] is True
    assert hits == [vectors.Hit("T", "txt", 0.5)]


def test_read_chunks_returns_stable_snapshot_without_vectors(monkeypatch):
    seen = {}
    atlas_obj = _Obj("ignored", "ignored")
    atlas_obj.properties = {
        "source": "C",
        "content": "charlie",
        "profile": "graph_native",
        "chunkIndex": 0,
    }

    class _Collection:
        def iterator(self, *, include_vector):
            seen["include_vector"] = include_vector
            return iter([_Obj("B", "beta"), atlas_obj, _Obj("A", "alpha")])

    class _Client:
        @property
        def collections(self):
            class _Collections:
                def get(self, name):
                    seen["collection"] = name
                    return _Collection()
            return _Collections()

        def close(self):
            seen["closed"] = True

    monkeypatch.setattr(vectors, "_weaviate", lambda: _Client())

    hits = vectors.read_chunks("RagBase")

    assert hits == [Hit("A", "alpha"), Hit("B", "beta"), Hit("C", "charlie")]
    assert seen == {"collection": "RagBase", "include_vector": False, "closed": True}


def test_rag_weaviate_grpc_port_validation(monkeypatch):
    import sys
    import types
    # the port parse (and its self-describing ValueError) happens before any
    # client construction, so an empty module stub suffices for the guard path.
    monkeypatch.setitem(sys.modules, "weaviate", types.ModuleType("weaviate"))
    monkeypatch.setenv("RAG_WEAVIATE_GRPC_PORT", "not-a-port")
    with pytest.raises(ValueError, match="RAG_WEAVIATE_GRPC_PORT"):
        vectors._weaviate()


@pytest.mark.asyncio
@respx.mock
async def test_rerank_warns_on_malformed_batch_env(monkeypatch, caplog):
    # A typo'd TEI_RERANKER_MAX_BATCH degrades to the default WITH a warning —
    # the guarded-parse contract the lightrag module credits this site with.
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    monkeypatch.setenv("TEI_RERANKER_MAX_BATCH", "not-a-number")
    respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json=[{"index": 0, "score": 0.9}]))
    with caplog.at_level("WARNING", logger="uvicorn.error"):
        out = await rerank("q", [Hit("T", "text", None)], top_n=1)
    assert [h.title for h in out] == ["T"]
    assert "TEI_RERANKER_MAX_BATCH" in caplog.text
