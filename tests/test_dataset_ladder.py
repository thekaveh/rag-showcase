from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _manifest() -> dict:
    return yaml.safe_load((ROOT / "compare" / "datasets.yaml").read_text(encoding="utf-8"))


def test_dataset_manifest_orders_inputs_by_complexity() -> None:
    manifest = _manifest()
    datasets = manifest["datasets"]

    levels = [d["complexity_level"] for d in datasets]
    assert levels == sorted(levels)
    assert [d["id"] for d in datasets[:2]] == ["baseline_curated", "graph_native"]
    assert len(datasets) >= 6

    for dataset in datasets:
        assert dataset["id"]
        assert dataset["label"]
        assert dataset["status"] in {"measured", "candidate"}
        assert dataset["graph_nature"]
        assert dataset["queries_file"].startswith("demo/")
        assert (ROOT / dataset["queries_file"]).is_file()


def test_measured_datasets_have_committed_result_snapshots() -> None:
    measured = [d for d in _manifest()["datasets"] if d["status"] == "measured"]
    assert {d["id"] for d in measured} >= {"baseline_curated", "graph_native"}

    for dataset in measured:
        assert (ROOT / dataset["matrix_snapshot"]).is_file()
        assert (ROOT / dataset["judgment_snapshot"]).is_file()


def test_candidate_dataset_queries_are_graph_heavy() -> None:
    candidates = [d for d in _manifest()["datasets"] if d["status"] == "candidate"]
    assert candidates

    for dataset in candidates:
        queries = yaml.safe_load((ROOT / dataset["queries_file"]).read_text(encoding="utf-8"))
        assert len(queries) >= 6
        for query in queries:
            assert query["id"]
            assert query["query"]
            assert query["expect_winner"] == "graph-rag"
            rationale = query.get("rationale", "").lower()
            assert any(word in rationale for word in ["relationship", "multi-hop", "graph", "path", "temporal"])


def test_cyber_dataset_has_committed_attack_corpus() -> None:
    manifest = _manifest()
    dataset = next(d for d in manifest["datasets"] if d["id"] == "cyber_threat_intel")
    corpus = ROOT / dataset["corpus_path"]

    assert corpus == ROOT / "corpus/cyber_threat_intel"
    docs = sorted(corpus.glob("*.md"))
    assert len(docs) >= 20
    joined = "\n".join(doc.read_text(encoding="utf-8") for doc in docs[:10])
    assert "MITRE ATT&CK Enterprise" in joined
    assert "Relations:" in joined


def test_cyber_queries_match_committed_attack_corpus_scope() -> None:
    queries = yaml.safe_load((ROOT / "demo/cyber_threat_intel_queries.yaml").read_text(encoding="utf-8"))
    text = "\n".join(q["query"] for q in queries).lower()

    assert "intrusion" in text
    assert "technique" in text
    assert "mitigation" in text
    assert "cve" not in text
    assert "product" not in text
