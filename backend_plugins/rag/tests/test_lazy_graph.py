import json

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from rag.approaches import lazy
from rag.common import flavors
from rag.common.lazy_graph import build_index, extract_concepts, load_or_build, retrieve
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
    assert graph_metrics["llm_index_calls"] == 0
    assert graph_metrics["relevance_tests"] >= 1
