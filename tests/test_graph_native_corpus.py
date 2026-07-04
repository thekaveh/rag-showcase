from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_graph_native_corpus_is_committed_and_relation_dense() -> None:
    docs = sorted((ROOT / "corpus" / "graph_native").glob("*.md"))

    assert len(docs) >= 8
    for doc in docs:
        text = doc.read_text(encoding="utf-8")
        assert "Source:" in text
        assert "Relations:" in text
        assert text.count("->") >= 3


def test_graph_native_queries_target_graph_reasoning() -> None:
    queries = yaml.safe_load((ROOT / "demo" / "graph_native_queries.yaml").read_text(encoding="utf-8"))

    assert len(queries) >= 6
    assert {q["id"] for q in queries} >= {
        "entity_bridge",
        "relationship_chain",
        "shared_actor",
        "timeline_cause",
    }
    assert sum(q.get("expect_winner") == "graph-rag" for q in queries) >= 4
    assert all("rationale" in q and q["rationale"] for q in queries)
