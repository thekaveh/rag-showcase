from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from compare.evaluation_summary import build_summary, write_summary, write_summary_csv


def _row(
    dataset: str,
    complexity: int,
    question: str,
    approach: str,
    *,
    status: str = "ok",
    latency: int = 100,
    faithfulness: float | None = 0.8,
    ragas_status: str = "ok",
) -> dict:
    scores = {} if faithfulness is None else {"faithfulness": faithfulness}
    not_evaluable = (
        {"faithfulness": "retrieved_contexts_required"}
        if ragas_status == "not_evaluable"
        else {}
    )
    return {
        "schema_version": 1,
        "runner_version": 1,
        "run_id": "run-1",
        "row_id": f"{dataset}-{question}-{approach}",
        "dataset": {"id": dataset, "label": dataset, "complexity_level": complexity},
        "question": {"id": question, "query": question},
        "approach": {"model": approach, "base_model": approach, "flavor": "default"},
        "status": status,
        "evidence": {"answer": "a" if status == "ok" else "", "contexts": []},
        "metrics": {
            "operational": {"latency_ms": latency, "attempts": 1},
            "ragas": {
                "status": ragas_status if status == "ok" else "not_run",
                "requested": ["faithfulness"],
                "scores": scores if status == "ok" else {},
                "not_evaluable": not_evaluable,
            },
            "judge_panel": {"status": "pending"},
        },
        "error": None if status == "ok" else {"type": "Error", "message": "failed"},
    }


def test_summary_reports_coverage_failures_ties_and_longitudinal_progression() -> None:
    rows = [
        _row("easy", 1, "q1", "a", latency=100, faithfulness=0.8),
        _row("easy", 1, "q2", "a", latency=200, faithfulness=None,
             ragas_status="not_evaluable"),
        _row("easy", 1, "q1", "b", latency=300, faithfulness=0.8),
        _row("easy", 1, "q2", "b", status="error", latency=50, faithfulness=None),
        _row("hard", 2, "q1", "a", latency=400, faithfulness=0.6),
        _row("hard", 2, "q1", "b", latency=500, faithfulness=0.9),
    ]

    summary = build_summary(list(reversed(rows)), judgments=None)

    assert summary["schema_version"] == 1
    easy = summary["datasets"]["easy"]
    assert easy["coverage"] == {
        "total_rows": 4,
        "ok": 3,
        "errors": 1,
        "timeouts": 0,
    }
    assert easy["approaches"]["a"]["ragas"]["faithfulness"] == {
        "mean": 0.8,
        "evaluated": 1,
        "total": 2,
        "not_evaluable": 1,
        "errors": 0,
        "timeouts": 0,
        "coverage": 0.5,
    }
    assert easy["approaches"]["b"]["operational"]["successful"] == 1
    assert easy["approaches"]["b"]["operational"]["errors"] == 1
    assert easy["rankings"]["ragas"]["faithfulness"][0] == {
        "rank": 1,
        "approaches": ["a", "b"],
        "value": 0.8,
        "coverage": {
            "a": {"evaluated": 1, "total": 2},
            "b": {"evaluated": 1, "total": 2},
        },
    }
    assert easy["rankings"]["operational"]["mean_latency_ms"][0]["approaches"] == ["a"]
    assert [point["dataset_id"] for point in summary["longitudinal"]["a"]] == ["easy", "hard"]
    assert summary["longitudinal"]["a"][1]["ragas"]["faithfulness"]["mean"] == 0.6


def test_summary_joins_judges_without_changing_other_metric_classes() -> None:
    rows = [
        _row("easy", 1, "q1", "a", faithfulness=0.8),
        _row("easy", 1, "q1", "b", faithfulness=0.7),
    ]
    judgments = {
        "dataset_id": "easy",
        "judges": ["judge-a", "judge-b"],
        "queries": [
            {
                "query_id": "q1",
                "mean_by_approach": {"a": 4.0, "b": 4.0},
                "per_judge": {"judge-a": {}, "judge-b": {}},
            }
        ],
    }

    without = build_summary(rows, judgments=None)
    with_judges = build_summary(rows, judgments=judgments)

    assert with_judges["overall"]["rankings"]["ragas"] == without["overall"]["rankings"]["ragas"]
    assert with_judges["overall"]["rankings"]["operational"] == without["overall"]["rankings"]["operational"]
    assert with_judges["datasets"]["easy"]["judge_panel"]["models"] == ["judge-a", "judge-b"]
    assert with_judges["datasets"]["easy"]["rankings"]["judge_panel"][0] == {
        "rank": 1,
        "approaches": ["a", "b"],
        "value": 4.0,
        "coverage": {
            "a": {"evaluated": 1, "total": 1},
            "b": {"evaluated": 1, "total": 1},
        },
    }


def test_judge_failure_has_explicit_zero_coverage_and_preserves_ragas() -> None:
    rows = [_row("easy", 1, "q1", "a", faithfulness=0.8)]
    judgments = {
        "dataset_id": "easy",
        "judges": ["judge-a"],
        "queries": [{
            "query_id": "q1",
            "mean_by_approach": {},
            "per_judge": {"judge-a": {"error": "no valid verdict"}},
        }],
    }

    summary = build_summary(rows, judgments=judgments)

    assert summary["datasets"]["easy"]["judge_panel"]["status"] == "error"
    assert summary["datasets"]["easy"]["judge_panel"]["evaluated_queries"] == 0
    assert summary["datasets"]["easy"]["approaches"]["a"]["ragas"]["faithfulness"]["mean"] == 0.8


def test_judge_query_coverage_counts_only_questions_with_scores() -> None:
    rows = [
        _row("easy", 1, "q1", "a"),
        _row("easy", 1, "q2", "a"),
    ]
    judgments = {
        "dataset_id": "easy",
        "judges": ["judge-a"],
        "queries": [
            {"query_id": "q1", "mean_by_approach": {"a": 4.0}},
            {"query_id": "q2", "mean_by_approach": {}},
        ],
    }

    summary = build_summary(rows, judgments)

    assert summary["datasets"]["easy"]["judge_panel"]["evaluated_queries"] == 1
    assert summary["datasets"]["easy"]["judge_panel"]["total_queries"] == 2
    assert summary["datasets"]["easy"]["approaches"]["a"]["judge_panel"]["coverage"] == 0.5


def test_write_summary_is_byte_stable_for_reordered_jsonl(tmp_path: Path) -> None:
    rows = [
        _row("easy", 1, "q1", "a", faithfulness=0.8),
        _row("easy", 1, "q1", "b", faithfulness=0.7),
    ]
    first_rows = tmp_path / "first.jsonl"
    second_rows = tmp_path / "second.jsonl"
    first_rows.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    second_rows.write_text(
        "".join(json.dumps(row) + "\n" for row in reversed(rows)), encoding="utf-8"
    )
    first = tmp_path / "first-summary.json"
    second = tmp_path / "second-summary.json"

    write_summary(first_rows, first)
    write_summary(second_rows, second)

    assert first.read_bytes() == second.read_bytes()


def test_write_summary_preserves_metrics_when_judgments_artifact_is_invalid(
    tmp_path: Path,
) -> None:
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text(json.dumps(_row("easy", 1, "q1", "a")) + "\n", encoding="utf-8")

    for judgments_path in (
        tmp_path / "missing.json",
        tmp_path / "malformed.json",
        tmp_path / "non-object.json",
        tmp_path / "invalid-shape.json",
    ):
        if judgments_path.name == "malformed.json":
            judgments_path.write_text("[not an object]", encoding="utf-8")
        elif judgments_path.name == "non-object.json":
            judgments_path.write_text("[]", encoding="utf-8")
        elif judgments_path.name == "invalid-shape.json":
            judgments_path.write_text('{"queries":["invalid"]}', encoding="utf-8")
        output = tmp_path / f"{judgments_path.stem}-summary.json"
        summary = write_summary(rows_path, output, judgments_path)

        judge = summary["datasets"]["easy"]["judge_panel"]
        assert judge["status"] == "error"
        assert judge["error"]
        assert summary["datasets"]["easy"]["approaches"]["a"]["ragas"][
            "faithfulness"
        ]["mean"] == 0.8


def test_summary_separates_metric_timeouts_from_errors(tmp_path: Path) -> None:
    summary = build_summary(
        [_row("easy", 1, "q1", "a", status="timeout", faithfulness=None)],
        judgments=None,
    )
    metric = summary["datasets"]["easy"]["approaches"]["a"]["ragas"]["faithfulness"]
    assert metric["errors"] == 0
    assert metric["timeouts"] == 1

    output = tmp_path / "summary.csv"
    write_summary_csv(summary, output)
    ragas_line = next(
        line for line in output.read_text(encoding="utf-8").splitlines()
        if line.startswith("dataset,easy,1,a,ragas,faithfulness")
    )
    assert ragas_line.endswith(",0,1,0")


def test_write_summary_csv_keeps_metric_classes_and_coverage_separate(tmp_path: Path) -> None:
    rows = [
        _row("easy", 1, "q1", "a", faithfulness=0.8),
        _row("easy", 1, "q2", "a", faithfulness=None,
             ragas_status="not_evaluable"),
    ]
    summary = build_summary(rows, judgments=None)
    output = tmp_path / "summary.csv"

    write_summary_csv(summary, output)

    assert output.read_text(encoding="utf-8").splitlines() == [
        "scope,dataset_id,complexity_level,approach,metric_class,metric,value,"
        "evaluated,total,coverage,errors,timeouts,not_evaluable",
        "dataset,easy,1,a,operational,mean_latency_ms,100.0,2,2,1.0,0,0,0",
        "dataset,easy,1,a,ragas,faithfulness,0.8,1,2,0.5,0,0,1",
        "dataset,easy,1,a,judge_panel,mean_score,,0,2,0.0,0,0,0",
        "overall,,,a,operational,mean_latency_ms,100.0,2,2,1.0,0,0,0",
        "overall,,,a,ragas,faithfulness,0.8,1,2,0.5,0,0,1",
        "overall,,,a,judge_panel,mean_score,,0,2,0.0,0,0,0",
    ]


def test_summarize_cli_help_runs_from_repo_root() -> None:
    root = Path(__file__).parents[1]
    result = subprocess.run(
        [sys.executable, "compare/summarize.py", "--help"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "--csv-output" in result.stdout
