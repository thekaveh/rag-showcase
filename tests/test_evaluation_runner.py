from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from compare.evaluation import (
    AtlasEvaluationClient,
    JsonlStore,
    QuestionSpec,
    SelectedApproach,
    load_dataset,
    load_manifest,
    run_evaluation,
)


def _manifest(tmp_path: Path, *, retries: int = 0) -> tuple[object, object]:
    (tmp_path / "questions").mkdir()
    (tmp_path / "corpus" / "a").mkdir(parents=True)
    (tmp_path / "datasets.yaml").write_text(
        """
datasets:
  - id: ds-a
    label: Dataset A
    complexity_level: 1
    status: measured
    corpus_path: corpus/a
    queries_file: questions/a.yaml
    graph_nature: relational
""",
        encoding="utf-8",
    )
    path = tmp_path / "evaluation.yaml"
    path.write_text(
        f"""
version: 1
datasets_file: datasets.yaml
approaches:
  - model: vanilla-rag
    evidence: answer_with_contexts
  - model: graph-rag
    evidence: answer_only
metrics:
  ragas: [faithfulness, answer_relevancy, context_recall]
  judge_panel:
    enabled: false
    models: []
run:
  retries: {retries}
  timeout_s: 10
  evaluator_timeout_s: 20
  concurrency: 1
  seed: test-seed
""",
        encoding="utf-8",
    )
    manifest = load_manifest(path)
    return manifest, load_dataset(manifest, "ds-a")


def _completion(model: str, answer: str = "answer") -> dict:
    return {
        "id": f"id-{model}",
        "model": model,
        "choices": [{"message": {"content": answer}}],
        "usage": {"prompt_tokens": 2, "completion_tokens": 3, "total_tokens": 5},
        "rag_showcase": {
            "schema_version": 1,
            "sources": [{"title": "Doc", "snippet": "grounding context", "score": 0.8}],
            "metrics": {"seconds": 1.0, "chunks": 1, "llm_calls": 2, "cloud_calls": 0},
        },
    }


class _Evaluator:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def evaluate(self, **kwargs) -> dict:
        self.calls.append(kwargs)
        return {
            "status": "ok",
            "requested": kwargs["metrics"],
            "scores": {metric: 0.75 for metric in kwargs["metrics"]},
            "not_evaluable": {},
            "evaluator_model": "judge-model",
            "embeddings_model": "embed-model",
        }


def test_run_evaluation_persists_every_2x2_cell_and_isolates_timeout(tmp_path: Path) -> None:
    manifest, dataset = _manifest(tmp_path)
    questions = [QuestionSpec(id="q1", query="one"), QuestionSpec(id="q2", query="two")]
    approaches = [
        SelectedApproach(model="vanilla-rag", base_model="vanilla-rag", flavor="default",
                         evidence="answer_with_contexts"),
        SelectedApproach(model="graph-rag", base_model="graph-rag", flavor="default",
                         evidence="answer_only"),
    ]
    calls: list[tuple[str, str]] = []

    def invoke(model: str, query: str, timeout_s: float) -> dict:
        calls.append((model, query))
        if model == "graph-rag" and query == "two":
            raise httpx.ReadTimeout("slow graph")
        return _completion(model, f"{model}: {query}")

    evaluator = _Evaluator()
    store = JsonlStore(tmp_path / "rows.jsonl")

    rows = run_evaluation(
        manifest=manifest,
        run_id="run-1",
        dataset=dataset,
        questions=questions,
        approaches=approaches,
        invoke=invoke,
        evaluator=evaluator,
        store=store,
    )

    assert len(rows) == 4
    assert len({row["row_id"] for row in rows}) == 4
    assert len(calls) == 4
    failed = next(row for row in rows if row["question"]["id"] == "q2"
                  and row["approach"]["model"] == "graph-rag")
    assert failed["status"] == "timeout"
    assert "ReadTimeout" in failed["error"]["type"]
    successful = [row for row in rows if row["status"] == "ok"]
    assert len(successful) == 3
    assert all(row["metrics"]["operational"]["latency_ms"] >= 0 for row in rows)
    assert all(row["metrics"]["judge_panel"]["status"] == "disabled" for row in rows)
    assert len((tmp_path / "rows.jsonl").read_text(encoding="utf-8").splitlines()) == 4

    graph_ok = next(row for row in rows if row["question"]["id"] == "q1"
                    and row["approach"]["model"] == "graph-rag")
    assert graph_ok["evidence"]["contexts"] == []
    assert graph_ok["metrics"]["ragas"]["status"] == "ok"  # fake evaluator result preserved
    graph_call = next(call for call in evaluator.calls if call["metadata"]["row_id"] == graph_ok["row_id"])
    assert graph_call["contexts"] == []


def test_run_evaluation_resume_skips_completed_rows_without_duplicates(tmp_path: Path) -> None:
    manifest, dataset = _manifest(tmp_path)
    questions = [QuestionSpec(id="q1", query="one"), QuestionSpec(id="q2", query="two")]
    approaches = [SelectedApproach(model="vanilla-rag", base_model="vanilla-rag",
                                   flavor="default", evidence="answer_with_contexts")]
    store = JsonlStore(tmp_path / "rows.jsonl")
    evaluator = _Evaluator()
    first_calls = 0

    def first_invoke(model: str, query: str, timeout_s: float) -> dict:
        nonlocal first_calls
        first_calls += 1
        return _completion(model, query)

    first = run_evaluation(
        manifest=manifest, run_id="run-1", dataset=dataset, questions=questions,
        approaches=approaches, invoke=first_invoke, evaluator=evaluator, store=store,
    )
    assert first_calls == 2

    def must_not_run(model: str, query: str, timeout_s: float) -> dict:
        raise AssertionError("completed cell was invoked during resume")

    resumed = run_evaluation(
        manifest=manifest, run_id="run-1", dataset=dataset, questions=questions,
        approaches=approaches, invoke=must_not_run, evaluator=evaluator,
        store=JsonlStore(tmp_path / "rows.jsonl"),
    )
    assert resumed == first
    assert len((tmp_path / "rows.jsonl").read_text(encoding="utf-8").splitlines()) == 2


def test_run_evaluation_resume_rejects_changed_configuration(tmp_path: Path) -> None:
    manifest, dataset = _manifest(tmp_path)
    questions = [QuestionSpec(id="q1", query="one")]
    approaches = [SelectedApproach(model="vanilla-rag", base_model="vanilla-rag",
                                   flavor="default", evidence="answer_with_contexts")]
    path = tmp_path / "rows.jsonl"
    run_evaluation(
        manifest=manifest, run_id="same-run", dataset=dataset, questions=questions,
        approaches=approaches, invoke=lambda *args: _completion("vanilla-rag"),
        evaluator=None, store=JsonlStore(path), config_hashes={"manifest": "old"},
    )

    with pytest.raises(ValueError, match="resume row.*configuration"):
        run_evaluation(
            manifest=manifest, run_id="same-run", dataset=dataset, questions=questions,
            approaches=approaches, invoke=lambda *args: _completion("vanilla-rag"),
            evaluator=None, store=JsonlStore(path), config_hashes={"manifest": "new"},
        )


def test_jsonl_store_rejects_duplicate_existing_row_ids(tmp_path: Path) -> None:
    row = {"row_id": "same", "status": "ok"}
    path = tmp_path / "rows.jsonl"
    path.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate row_id.*same"):
        JsonlStore(path).rows()


@respx.mock
def test_atlas_evaluator_calls_only_eligible_metrics_and_records_models() -> None:
    route = respx.post("http://atlas.test/api/rag/evaluate").mock(
        return_value=httpx.Response(
            200,
            json={
                "metrics": ["faithfulness"],
                "record_count": 1,
                "evaluator_model": "eval-model",
                "embeddings_model": "embed-model",
                "results": [{"record_index": 0, "scores": {"faithfulness": 0.8}, "metadata": {}}],
                "metadata": {"runner": "ragas"},
            },
        )
    )
    client = AtlasEvaluationClient("http://atlas.test/api/rag/evaluate", timeout_s=2, retries=0)

    result = client.evaluate(
        question="q",
        answer="a",
        contexts=["context"],
        reference=None,
        metrics=["faithfulness", "context_recall"],
        metadata={"row_id": "r1"},
    )
    client.close()

    assert route.called
    request = json.loads(route.calls[0].request.content)
    assert request["metrics"] == ["faithfulness"]
    assert request["records"][0]["metadata"]["row_id"] == "r1"
    assert result["status"] == "partial"
    assert result["scores"] == {"faithfulness": 0.8}
    assert result["not_evaluable"] == {"context_recall": "ground_truth_required"}
    assert result["evaluator_model"] == "eval-model"
    assert result["embeddings_model"] == "embed-model"


@respx.mock
def test_atlas_evaluator_marks_missing_contexts_without_http_call() -> None:
    route = respx.post("http://atlas.test/api/rag/evaluate")
    client = AtlasEvaluationClient("http://atlas.test/api/rag/evaluate", timeout_s=2)

    result = client.evaluate(
        question="q", answer="a", contexts=[], reference="truth",
        metrics=["faithfulness", "answer_relevancy"], metadata={},
    )
    client.close()

    assert not route.called
    assert result["status"] == "not_evaluable"
    assert result["not_evaluable"] == {
        "faithfulness": "retrieved_contexts_required",
        "answer_relevancy": "retrieved_contexts_required",
    }


@respx.mock
def test_atlas_evaluator_failure_is_metric_error_not_lost_answer() -> None:
    respx.post("http://atlas.test/api/rag/evaluate").mock(
        return_value=httpx.Response(503, json={"detail": "evaluator unavailable"})
    )
    client = AtlasEvaluationClient("http://atlas.test/api/rag/evaluate", timeout_s=2, retries=0)

    result = client.evaluate(
        question="q", answer="a", contexts=["c"], reference=None,
        metrics=["faithfulness"], metadata={},
    )
    client.close()

    assert result["status"] == "error"
    assert result["scores"] == {}
    assert "503" in result["error"]
