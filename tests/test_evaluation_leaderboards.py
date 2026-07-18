from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

from compare.leaderboards import (
    build_leaderboards,
    competition_ranks,
    mean_pairwise_disagreement,
)


def _metric(
    mean: float | None,
    evaluated: int,
    total: int,
    *,
    not_evaluable: int = 0,
    errors: int = 0,
    timeouts: int = 0,
) -> dict[str, Any]:
    return {
        "mean": mean,
        "evaluated": evaluated,
        "total": total,
        "not_evaluable": not_evaluable,
        "errors": errors,
        "timeouts": timeouts,
        "coverage": round(evaluated / total, 6) if total else 0.0,
    }


def _approach_summary(
    judge_mean: float | None,
    judge_evaluated: int,
    judge_total: int,
    *,
    answer_relevancy: dict[str, Any] | None = None,
    faithfulness: dict[str, Any] | None = None,
    latency: float | None = 100.0,
    successful: int | None = None,
    attempted: int | None = None,
    errors: int = 0,
    timeouts: int = 0,
) -> dict[str, Any]:
    total = judge_total if attempted is None else attempted
    ok = total if successful is None else successful
    return {
        "judge_panel": {
            "mean": judge_mean,
            "evaluated": judge_evaluated,
            "total": judge_total,
            "coverage": round(judge_evaluated / judge_total, 6) if judge_total else 0.0,
        },
        "ragas": {
            "answer_relevancy": answer_relevancy or _metric(0.5, total, total),
            "faithfulness": faithfulness or _metric(0.6, total, total),
        },
        "operational": {
            "attempted": total,
            "successful": ok,
            "errors": errors,
            "timeouts": timeouts,
            "mean_latency_ms": latency,
            "error_rate": round((errors + timeouts) / total, 6) if total else 0.0,
        },
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _write_snapshot(
    root: Path,
    dataset_id: str,
    *,
    tier: str,
    approaches: dict[str, dict[str, Any]],
    queries: list[dict[str, Any]],
) -> tuple[str, str]:
    prefix = f"results/{dataset_id}-{tier}"
    _write_json(
        root / f"{prefix}-evaluation.json",
        {"datasets": {dataset_id: {"approaches": approaches}}},
    )
    _write_json(
        root / f"{prefix}-judgments.json",
        {
            "dataset_id": dataset_id,
            "judges": ["judge-a", "judge-b"],
            "queries": queries,
        },
    )
    return f"{prefix}-evaluation.json", f"{prefix}-judgments.json"


def _query(
    query_id: str,
    scores: dict[str, float],
    *,
    per_judge: dict[str, dict[str, float]],
    winner: str,
) -> dict[str, Any]:
    return {
        "query_id": query_id,
        "mean_by_approach": scores,
        "per_judge": {
            model: {"scores": model_scores} for model, model_scores in per_judge.items()
        },
        "observed_winner": winner,
    }


def _write_two_dataset_fixture(tmp_path: Path) -> list[dict[str, Any]]:
    base_one = {
        "approach-a": _approach_summary(
            2.0,
            1,
            1,
            answer_relevancy=_metric(0.2, 1, 1),
            faithfulness=_metric(0.4, 1, 1),
            latency=100.0,
        ),
        "approach-b": _approach_summary(
            3.0,
            1,
            1,
            answer_relevancy=_metric(0.8, 1, 1),
            faithfulness=_metric(0.7, 1, 1),
            latency=200.0,
        ),
    }
    base_two = {
        "approach-a": _approach_summary(
            5.0,
            3,
            3,
            answer_relevancy=_metric(0.8, 3, 3),
            faithfulness=_metric(0.9, 2, 3, not_evaluable=1),
            latency=300.0,
            successful=2,
            attempted=3,
            errors=1,
        ),
        "approach-b": _approach_summary(
            3.0,
            3,
            3,
            answer_relevancy=_metric(0.4, 3, 3),
            faithfulness=_metric(0.5, 3, 3),
            latency=500.0,
        ),
    }
    queries_one = [
        _query(
            "q1",
            {"approach-a": 2.0, "approach-b": 3.0},
            per_judge={
                "judge-a": {"approach-a": 1.0, "approach-b": 3.0},
                "judge-b": {"approach-a": 3.0, "approach-b": 3.0},
            },
            winner="approach-b",
        )
    ]
    queries_two = [
        _query(
            f"q{index}",
            {"approach-a": 5.0, "approach-b": 3.0},
            per_judge={
                "judge-a": {"approach-a": 4.0, "approach-b": 3.0},
                "judge-b": {"approach-a": 6.0, "approach-b": 3.0},
            },
            winner="approach-a",
        )
        for index in range(1, 4)
    ]
    first_eval, first_judgments = _write_snapshot(
        tmp_path, "easy", tier="base", approaches=base_one, queries=queries_one
    )
    second_eval, second_judgments = _write_snapshot(
        tmp_path, "hard", tier="base", approaches=base_two, queries=queries_two
    )
    return [
        {
            "id": "easy",
            "complexity_level": 1,
            "status": "measured",
            "evaluation_snapshot": first_eval,
            "judgment_snapshot": first_judgments,
        },
        {
            "id": "hard",
            "complexity_level": 2,
            "status": "measured",
            "evaluation_snapshot": second_eval,
            "judgment_snapshot": second_judgments,
        },
    ]


def _write_graph_ineligible_fixture(tmp_path: Path) -> list[dict[str, Any]]:
    approaches = {
        "graph-rag": _approach_summary(
            4.0,
            2,
            2,
            faithfulness=_metric(None, 0, 2, not_evaluable=2),
        )
    }
    queries = [
        _query(
            f"q{index}",
            {"graph-rag": 4.0},
            per_judge={
                "judge-a": {"graph-rag": 4.0},
                "judge-b": {"graph-rag": 4.0},
            },
            winner="graph-rag",
        )
        for index in range(1, 3)
    ]
    evaluation, judgments = _write_snapshot(
        tmp_path, "graph", tier="base", approaches=approaches, queries=queries
    )
    return [{
        "id": "graph",
        "complexity_level": 1,
        "status": "measured",
        "evaluation_snapshot": evaluation,
        "judgment_snapshot": judgments,
    }]


def test_overall_rank_uses_dataset_macro_mean(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)

    result = build_leaderboards(datasets, root=tmp_path)
    rows = {row["approach"]: row for row in result["base"]["overall"]}

    assert rows["approach-a"]["judge_macro_mean"] == 3.5
    assert rows["approach-a"]["judge_weighted_mean"] == 4.25
    assert rows["approach-b"]["judge_macro_mean"] == 3.0
    assert rows["approach-a"]["overall_rank"] == 1
    assert rows["approach-a"]["judge_evaluated"] == 4
    assert rows["approach-a"]["judge_total"] == 4


def test_aggregates_counters_models_disagreement_and_weighted_metrics(
    tmp_path: Path,
) -> None:
    result = build_leaderboards(_write_two_dataset_fixture(tmp_path), root=tmp_path)
    row = next(row for row in result["base"]["overall"] if row["approach"] == "approach-a")

    assert row["judge_by_model"] == {"judge-a": 3.25, "judge-b": 5.25}
    assert row["judge_disagreement"] == 2.0
    assert row["mean_dataset_rank"] == 1.5
    assert row["best_dataset_rank"] == 1
    assert row["worst_dataset_rank"] == 2
    assert row["query_wins"] == 3
    assert row["answer_relevancy_mean"] == 0.65
    assert row["answer_relevancy_evaluated"] == 4
    assert row["faithfulness_mean"] == 0.733333
    assert row["faithfulness_evaluated"] == 3
    assert row["faithfulness_not_evaluable"] == 1
    assert row["mean_latency_ms"] == 233.333333
    assert row["successful"] == 3
    assert row["attempted"] == 4
    assert row["errors"] == 1
    assert row["timeouts"] == 0
    assert row["error_rate"] == 0.25


def test_missing_faithfulness_is_not_coerced_to_zero(tmp_path: Path) -> None:
    datasets = _write_graph_ineligible_fixture(tmp_path)
    row = build_leaderboards(datasets, root=tmp_path)["base"]["overall"][0]

    assert row["faithfulness_mean"] is None
    assert row["faithfulness_evaluated"] == 0
    assert row["faithfulness_not_evaluable"] == 2


def test_base_and_flavor_aliases_are_separate(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    flavors = {
        "flavors": [{"alias": "approach-a-wide", "base": "approach-a"}],
    }
    flavors_path = tmp_path / "compare" / "flavors.yaml"
    flavors_path.parent.mkdir()
    flavors_path.write_text(yaml.safe_dump(flavors), encoding="utf-8")
    approaches = {"approach-a-wide": _approach_summary(4.0, 1, 1)}
    queries = [
        _query(
            "q1",
            {"approach-a-wide": 4.0},
            per_judge={
                "judge-a": {"approach-a-wide": 4.0},
                "judge-b": {"approach-a-wide": 4.0},
            },
            winner="approach-a-wide",
        )
    ]
    for dataset in datasets:
        evaluation, judgments = _write_snapshot(
            tmp_path,
            dataset["id"],
            tier="flavor",
            approaches=approaches,
            queries=queries,
        )
        dataset["flavor_evaluation_snapshot"] = evaluation
        dataset["flavor_judgment_snapshot"] = judgments

    result = build_leaderboards(datasets, root=tmp_path)

    assert {row["approach"] for row in result["base"]["overall"]} == {
        "approach-a", "approach-b"
    }
    assert result["flavors"]["overall"][0]["approach"] == "approach-a-wide"
    assert result["flavors"]["overall"][0]["base_family"] == "approach-a"
    assert result["base"]["dataset_count"] == 2
    assert result["flavors"]["judge_models"] == ["judge-a", "judge-b"]


def test_validation_rejects_incompatible_measured_snapshots(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["judgment_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["queries"][0].pop("mean_by_approach")
    _write_json(path, artifact)

    with pytest.raises(ValueError, match="mean_by_approach"):
        build_leaderboards(datasets, root=tmp_path)


def test_competition_ranks_preserve_ties() -> None:
    assert competition_ranks(
        {"a": 4.0, "b": 4.0, "c": 3.0}, higher_is_better=True
    ) == {"a": 1, "b": 1, "c": 3}


def test_mean_pairwise_disagreement() -> None:
    assert mean_pairwise_disagreement([[1.0, 3.0], [2.0, 5.0]]) == 2.5
    assert mean_pairwise_disagreement([[4.0]]) is None
