from __future__ import annotations

import json
from pathlib import Path

import pytest

from compare.evaluation import (
    completion_evidence,
    evidence_for_base,
    load_dataset,
    load_manifest,
)


def _write_manifest(tmp_path: Path, *, overrides: str = "") -> Path:
    datasets = tmp_path / "datasets.yaml"
    datasets.write_text(
        """
datasets:
  - id: ds-a
    label: Dataset A
    complexity_level: 1
    status: measured
    corpus_path: corpus/a
    queries_file: questions/a.yaml
    graph_nature: textual
""",
        encoding="utf-8",
    )
    manifest = tmp_path / "evaluation.yaml"
    manifest.write_text(
        """
version: 1
datasets_file: datasets.yaml
approaches:
  - model: vanilla-rag
    evidence: answer_with_contexts
  - model: graph-rag
    evidence: answer_only
metrics:
  ragas: [faithfulness, answer_relevancy]
  judge_panel:
    enabled: true
    endpoint: http://localhost:11434/v1/chat/completions
    temperature: 0
    thinking: false
    models: [judge-a]
run:
  retries: 1
  timeout_s: 30
  evaluator_timeout_s: 60
  concurrency: 1
  seed: stable-seed
"""
        + overrides,
        encoding="utf-8",
    )
    return manifest


def test_manifest_resolves_dataset_catalog_and_evidence_capability(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path)

    manifest = load_manifest(path)
    dataset = load_dataset(manifest, "ds-a")

    assert manifest.version == 1
    assert manifest.metrics.judge_panel.endpoint == "http://localhost:11434/v1/chat/completions"
    assert manifest.metrics.judge_panel.thinking is False
    assert manifest.datasets_file == tmp_path / "datasets.yaml"
    assert dataset.id == "ds-a"
    assert dataset.questions_file == tmp_path / "questions" / "a.yaml"
    assert dataset.corpus_path == tmp_path / "corpus" / "a"
    assert evidence_for_base(manifest, "vanilla-rag") == "answer_with_contexts"
    assert evidence_for_base(manifest, "graph-rag") == "answer_only"


@pytest.mark.parametrize(
    ("replacement", "message"),
    [
        ("version: 2", "version"),
        ("timeout_s: 0", "timeout"),
        ("concurrency: 0", "concurrency"),
        ("ragas: [not-a-metric]", "not-a-metric"),
        ("models: []", "models"),
        ("endpoint: ''", "endpoint"),
    ],
)
def test_manifest_rejects_invalid_contract(
    tmp_path: Path, replacement: str, message: str
) -> None:
    path = _write_manifest(tmp_path)
    text = path.read_text(encoding="utf-8")
    if replacement.startswith("version:"):
        text = text.replace("version: 1", replacement)
    elif replacement.startswith("timeout_s:"):
        text = text.replace("timeout_s: 30", replacement)
    elif replacement.startswith("concurrency:"):
        text = text.replace("concurrency: 1", replacement)
    elif replacement.startswith("ragas:"):
        text = text.replace("ragas: [faithfulness, answer_relevancy]", replacement)
    elif replacement.startswith("models:"):
        text = text.replace("models: [judge-a]", replacement)
    else:
        text = text.replace("endpoint: http://localhost:11434/v1/chat/completions", replacement)
    path.write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_manifest(path)


def test_manifest_rejects_duplicate_dataset_and_approach_ids(tmp_path: Path) -> None:
    path = _write_manifest(tmp_path)
    datasets = tmp_path / "datasets.yaml"
    datasets.write_text(
        datasets.read_text(encoding="utf-8")
        + """
  - id: ds-a
    label: Duplicate
    complexity_level: 2
    status: measured
    corpus_path: corpus/b
    queries_file: questions/b.yaml
    graph_nature: graph
""",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="duplicate dataset.*ds-a"):
        load_manifest(path)

    datasets.write_text(
        datasets.read_text(encoding="utf-8").split("  - id: ds-a", 2)[0]
        + """
  - id: ds-a
    label: Dataset A
    complexity_level: 1
    status: measured
    corpus_path: corpus/a
    queries_file: questions/a.yaml
    graph_nature: textual
""",
        encoding="utf-8",
    )
    text = path.read_text(encoding="utf-8").replace(
        "  - model: graph-rag\n    evidence: answer_only",
        "  - model: vanilla-rag\n    evidence: answer_only",
    )
    path.write_text(text, encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate approach.*vanilla-rag"):
        load_manifest(path)


def test_completion_evidence_prefers_structured_extension() -> None:
    payload = {
        "id": "response-1",
        "model": "vanilla-rag",
        "choices": [{"message": {"content": "answer with rendered fallback"}}],
        "usage": {"prompt_tokens": 3, "completion_tokens": 4, "total_tokens": 7},
        "rag_showcase": {
            "schema_version": 1,
            "sources": [{"title": "Doc A", "snippet": "alpha context", "score": 0.7}],
            "metrics": {"seconds": 1.2, "chunks": 1, "llm_calls": 2, "cloud_calls": 0},
        },
    }

    evidence = completion_evidence(payload)

    assert evidence["answer"] == "answer with rendered fallback"
    assert evidence["contexts"] == ["alpha context"]
    assert evidence["sources"] == [
        {"title": "Doc A", "snippet": "alpha context", "score": 0.7}
    ]
    assert evidence["server_metrics"]["llm_calls"] == 2
    assert evidence["token_usage"]["total_tokens"] == 7
    assert evidence["response_id"] == "response-1"
    assert evidence["transport"] == "structured"


def test_completion_evidence_parses_nested_multiline_rendered_sources() -> None:
    content = (
        "the answer"
        "\n\n<details><summary>🔎 Retrieved context (2 sources)</summary>\n"
        "\n**1. Doc A** · score 0.500\n\n> line one\nline two\n"
        "\n**2. Doc B**\n\n> second context\n\n</details>"
        "\n\n---\n📊 2.0s · 2 chunks · 2 LLM calls · 0 cloud"
        "\n\n<details><summary>🔎 Retrieved context (1 source)</summary>\n"
        "\n**1. Route**\n\n> complex\n\n</details>"
        "\n\n---\n📊 3.0s · 0 chunks · 1 LLM call · 0 cloud"
    )
    payload = {
        "id": "response-2",
        "choices": [{"message": {"content": content}}],
        "usage": {},
    }

    evidence = completion_evidence(json.loads(json.dumps(payload)))

    assert evidence["answer"] == "the answer"
    assert evidence["contexts"] == ["line one\nline two", "second context", "complex"]
    assert [source["title"] for source in evidence["sources"]] == ["Doc A", "Doc B", "Route"]
    assert evidence["server_metrics"]["seconds"] == 3.0
    assert evidence["transport"] == "rendered"
