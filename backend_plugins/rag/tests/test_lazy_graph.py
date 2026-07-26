import json
import threading
import time

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rag.common import lazy_graph
from rag.approaches import lazy
from rag.common import flavors
from rag.common.lazy_graph import (
    GraphChunk, GraphIndex, build_index, chunk_id, extract_concepts, load_or_build, retrieve,
)
from rag.common.vectors import Hit


@pytest.fixture(autouse=True)
def _clear_flavor_cache():
    flavors._CACHE.clear()
    yield
    flavors._CACHE.clear()


def _chunks():
    return [
        Hit("Operation Honeybee", "Operation Honeybee uses PowerShell T1059.001."),
        Hit("PowerShell", "PowerShell implements Command and Scripting Interpreter."),
        Hit("Mitigation", "User training mitigates spearphishing campaigns."),
    ]


def test_extract_concepts_is_deterministic_and_keeps_identifiers():
    text = "Operation Honeybee uses PowerShell T1059.001. Operation Honeybee persists."

    first = extract_concepts(text, max_concepts=8)
    second = extract_concepts(text, max_concepts=8)

    assert first == second
    assert "operation honeybee" in first
    assert "t1059.001" in first
    assert len(first) <= 8


def test_disk_cache_is_reused_and_invalidated_by_chunk_content(tmp_path):
    first, first_stats = load_or_build(_chunks(), cache_dir=tmp_path, namespace="test")
    second, second_stats = load_or_build(_chunks(), cache_dir=tmp_path, namespace="test")
    changed = _chunks() + [Hit("New", "A new relationship changes the corpus digest.")]
    third, third_stats = load_or_build(changed, cache_dir=tmp_path, namespace="test")
    fourth, fourth_stats = load_or_build(
        changed,
        cache_dir=tmp_path,
        namespace="test",
        max_concepts_per_chunk=8,
    )

    assert first_stats.cache_hit is False
    assert second_stats.cache_hit is True
    assert third_stats.cache_hit is False
    assert fourth_stats.cache_hit is False
    assert first.fingerprint == second.fingerprint
    assert third.fingerprint != first.fingerprint
    assert fourth.fingerprint != third.fingerprint
    stored = json.loads((tmp_path / "test.json").read_text(encoding="utf-8"))
    assert stored["fingerprint"] == fourth.fingerprint


def test_concurrent_cold_cache_requests_build_only_once(tmp_path, monkeypatch):
    # A burst of concurrent requests on a cold cache (first request, or right after
    # a corpus change) must not each redundantly run build_index() — the first
    # caller builds while the rest wait on the per-namespace lock, then see the
    # fresh cache file.
    real_build_index = lazy_graph.build_index
    calls = {"n": 0}

    def slow_build_index(*args, **kwargs):
        calls["n"] += 1
        time.sleep(0.1)  # widen the race window so a lock bug would reliably show
        return real_build_index(*args, **kwargs)

    monkeypatch.setattr(lazy_graph, "build_index", slow_build_index)

    results = []
    errors = []
    start = threading.Barrier(6)  # 5 workers + this thread, so all 5 race together

    def worker():
        try:
            start.wait(timeout=5)
            results.append(
                load_or_build(_chunks(), cache_dir=tmp_path, namespace="concurrent")
            )
        except Exception as exc:  # pragma: no cover - surfaced via `errors` assertion
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    start.wait(timeout=5)
    for thread in threads:
        thread.join(timeout=10)

    assert not errors
    assert len(results) == 5
    assert calls["n"] == 1  # only the lock winner actually built
    fingerprints = {index.fingerprint for index, _ in results}
    assert len(fingerprints) == 1  # every caller got the same, correctly-built index


def test_structurally_corrupt_cache_is_rebuilt(tmp_path):
    cache = tmp_path / "test.json"
    cache.write_text(
        json.dumps({
            "version": 1,
            "fingerprint": "not-the-corpus",
            "chunks": {},
            "concept_chunks": {},
            "edges": {"broken": None},
        }),
        encoding="utf-8",
    )

    index, stats = load_or_build(_chunks(), cache_dir=tmp_path, namespace="test")

    assert stats.cache_hit is False
    assert len(index.chunks) == len(_chunks())
    assert json.loads(cache.read_text(encoding="utf-8"))["fingerprint"] == index.fingerprint


def test_retrieve_enforces_relevance_and_context_budgets():
    index = build_index(_chunks())

    result = retrieve(
        index,
        "Which campaign uses PowerShell?",
        seed_hits=[_chunks()[0]],
        relevance_budget=1,
        max_context_chunks=1,
    )

    assert result.relevance_tests <= 1
    assert len(result.hits) <= 1
    assert result.hits[0].title == "Operation Honeybee"


def test_retrieve_weights_neighbor_expansion_by_edge_strength():
    # Score propagated to a neighbor's chunks must scale with that edge's weight
    # relative to the strongest edge from the just-visited concept
    # (score * 0.5 * (weight / max_weight)) — not just "reachable at all". Build
    # an index by hand so edge weights are exact, and give the WEAKER neighbor's
    # chunk an alphabetically-EARLIER title than the stronger neighbor's: if the
    # weight factor were ever dropped, both neighbors would tie on raw score and
    # the final ranking's title tie-break would flip weak ahead of strong — only
    # genuine proportional weighting keeps strong ranked ahead of weak here.
    seed_hit = Hit("Seed Chunk", "seed content")
    strong_hit = Hit("ZZZ Strong Chunk", "strong content")
    weak_hit = Hit("AAA Weak Chunk", "weak content")
    seed_id, strong_id, weak_id = chunk_id(seed_hit), chunk_id(strong_hit), chunk_id(weak_hit)

    index = GraphIndex(
        fingerprint="test",
        chunks={
            seed_id: GraphChunk(seed_id, seed_hit.title, seed_hit.text, ("seed",)),
            strong_id: GraphChunk(strong_id, strong_hit.title, strong_hit.text, ("strong",)),
            weak_id: GraphChunk(weak_id, weak_hit.title, weak_hit.text, ("weak",)),
        },
        concept_chunks={"seed": (seed_id,), "strong": (strong_id,), "weak": (weak_id,)},
        edges={
            "seed": {"strong": 10, "weak": 1},
            "strong": {"seed": 10},
            "weak": {"seed": 1},
        },
    )

    result = retrieve(
        index,
        "irrelevant question with no matching concepts",
        seed_hits=[seed_hit],
        relevance_budget=3,
        max_context_chunks=3,
    )

    assert [hit.title for hit in result.hits] == [
        "Seed Chunk", "ZZZ Strong Chunk", "AAA Weak Chunk",
    ]


def test_retrieve_falls_back_to_seed_hits_when_nothing_scores():
    # A question whose extracted concepts don't appear anywhere in the index, with
    # no seed hits either, means chunk_scores stays empty (Counter()) — the
    # fallback branch (hits = seed_hits[:max_context_chunks]) must return [], not
    # raise or return an unrelated chunk.
    index = build_index(_chunks())

    result = retrieve(
        index,
        "aardvark zebra unrelated question",
        seed_hits=[],
        relevance_budget=4,
        max_context_chunks=2,
    )

    assert result.hits == []
    assert result.relevance_tests == 0


@pytest.mark.asyncio
async def test_lazy_graph_route_returns_openai_shape_sources_and_graph_metrics(
    tmp_path, monkeypatch
):
    monkeypatch.setenv("LAZY_GRAPH_CACHE_DIR", str(tmp_path))

    async def fake_embed(texts):
        assert texts == ["Which campaign uses PowerShell?"]
        return [[0.1, 0.2]]

    async def fake_answer(model, question, hits):
        assert hits
        return "Operation Honeybee uses PowerShell.", 1

    monkeypatch.setattr(lazy.litellm, "embed", fake_embed)
    monkeypatch.setattr(lazy.config, "role", lambda name: "generator-model")
    monkeypatch.setattr(lazy, "answer_from_context", fake_answer)
    monkeypatch.setattr(lazy.vectors, "search_hybrid", lambda *args, **kwargs: [_chunks()[0]])
    monkeypatch.setattr(lazy.vectors, "read_chunks", lambda collection: _chunks())

    app = FastAPI()
    app.include_router(lazy.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as client:
        response = await client.post(
            "/lazy-graph-rag/v1/chat/completions",
            json={
                "model": "lazy-graph-rag",
                "messages": [{"role": "user", "content": "Which campaign uses PowerShell?"}],
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["model"] == "lazy-graph-rag"
    assert "Operation Honeybee uses PowerShell" in payload["choices"][0]["message"]["content"]
    assert "Retrieved context" in payload["choices"][0]["message"]["content"]
    graph_metrics = payload["rag_showcase"]["lazy_graph"]
    assert graph_metrics["cache_hit"] is False
    assert graph_metrics["cache_namespace"] == f"{lazy.COLLECTION}.concepts-24"
    assert (tmp_path / f"{lazy.COLLECTION}.concepts-24.json").is_file()
    assert graph_metrics["llm_index_calls"] == 0
    assert graph_metrics["relevance_tests"] >= 1
