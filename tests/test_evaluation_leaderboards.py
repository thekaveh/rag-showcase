from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

from compare import report_leaderboards
from compare.leaderboards import (
    _mean,
    _weighted_mean,
    build_leaderboards,
    competition_ranks,
    mean_pairwise_disagreement,
)


ROOT = Path(__file__).resolve().parents[1]


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


def _write_manifests(
    root: Path, *, base_approaches: list[str], flavors: list[dict[str, str]]
) -> None:
    compare = root / "compare"
    compare.mkdir(parents=True, exist_ok=True)
    (compare / "evaluation.yaml").write_text(
        yaml.safe_dump({"approaches": [{"model": name} for name in base_approaches]}),
        encoding="utf-8",
    )
    (compare / "flavors.yaml").write_text(
        yaml.safe_dump({"flavors": flavors}), encoding="utf-8"
    )


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
    per_judge: dict[str, dict[str, Any]],
    winner: str | None,
) -> dict[str, Any]:
    return {
        "query_id": query_id,
        "mean_by_approach": scores,
        "per_judge": {
            model: detail if "error" in detail else {"scores": detail}
            for model, detail in per_judge.items()
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
            4,
            answer_relevancy=_metric(0.8, 3, 4, errors=1),
            faithfulness=_metric(0.9, 2, 4, not_evaluable=1, errors=1),
            latency=300.0,
            successful=3,
            attempted=4,
            errors=1,
        ),
        "approach-b": _approach_summary(
            3.0,
            3,
            4,
            answer_relevancy=_metric(0.4, 4, 4),
            faithfulness=_metric(0.5, 4, 4),
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
                "judge-a": {"approach-a": 5.0, "approach-b": 3.0},
                "judge-b": {"approach-a": 5.0, "approach-b": 3.0},
            },
            winner="approach-a",
        )
        for index in range(1, 4)
    ]
    queries_two.append(
        _query(
            "q4",
            {},
            per_judge={
                "judge-a": {"error": "no valid verdict"},
                "judge-b": {"error": "no valid verdict"},
            },
            winner=None,
        )
    )
    first_eval, first_judgments = _write_snapshot(
        tmp_path, "easy", tier="base", approaches=base_one, queries=queries_one
    )
    second_eval, second_judgments = _write_snapshot(
        tmp_path, "hard", tier="base", approaches=base_two, queries=queries_two
    )
    datasets = [
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
    _write_manifests(
        tmp_path,
        base_approaches=["approach-a", "approach-b"],
        flavors=[{"alias": "approach-a-wide", "base": "approach-a"}],
    )
    flavor_approaches = {"approach-a-wide": _approach_summary(4.0, 1, 1)}
    flavor_queries = [
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
            approaches=flavor_approaches,
            queries=flavor_queries,
        )
        dataset["flavor_evaluation_snapshot"] = evaluation
        dataset["flavor_judgment_snapshot"] = judgments
    return datasets


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
    _write_manifests(
        tmp_path,
        base_approaches=["graph-rag"],
        flavors=[{"alias": "graph-rag-wide", "base": "graph-rag"}],
    )
    flavor_approaches = {"graph-rag-wide": _approach_summary(4.0, 2, 2)}
    flavor_queries = [
        _query(
            f"q{index}",
            {"graph-rag-wide": 4.0},
            per_judge={
                "judge-a": {"graph-rag-wide": 4.0},
                "judge-b": {"graph-rag-wide": 4.0},
            },
            winner="graph-rag-wide",
        )
        for index in range(1, 3)
    ]
    flavor_evaluation, flavor_judgments = _write_snapshot(
        tmp_path,
        "graph",
        tier="flavor",
        approaches=flavor_approaches,
        queries=flavor_queries,
    )
    return [{
        "id": "graph",
        "complexity_level": 1,
        "status": "measured",
        "evaluation_snapshot": evaluation,
        "judgment_snapshot": judgments,
        "flavor_evaluation_snapshot": flavor_evaluation,
        "flavor_judgment_snapshot": flavor_judgments,
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
    assert rows["approach-a"]["judge_total"] == 5


def test_aggregates_counters_models_disagreement_and_weighted_metrics(
    tmp_path: Path,
) -> None:
    result = build_leaderboards(_write_two_dataset_fixture(tmp_path), root=tmp_path)
    row = next(row for row in result["base"]["overall"] if row["approach"] == "approach-a")

    assert row["judge_by_model"] == {"judge-a": 4.0, "judge-b": 4.5}
    assert row["judge_disagreement"] == 0.5
    assert row["mean_dataset_rank"] == 1.5
    assert row["best_dataset_rank"] == 1
    assert row["worst_dataset_rank"] == 2
    assert row["query_wins"] == 3
    assert row["answer_relevancy_mean"] == 0.65
    assert row["answer_relevancy_evaluated"] == 4
    assert row["faithfulness_mean"] == 0.733333
    assert row["faithfulness_evaluated"] == 3
    assert row["faithfulness_not_evaluable"] == 1
    assert row["mean_latency_ms"] == 250.0
    assert row["successful"] == 4
    assert row["attempted"] == 5
    assert row["errors"] == 1
    assert row["timeouts"] == 0
    assert row["error_rate"] == 0.2


def test_missing_faithfulness_is_not_coerced_to_zero(tmp_path: Path) -> None:
    datasets = _write_graph_ineligible_fixture(tmp_path)
    row = build_leaderboards(datasets, root=tmp_path)["base"]["overall"][0]

    assert row["faithfulness_mean"] is None
    assert row["faithfulness_evaluated"] == 0
    assert row["faithfulness_not_evaluable"] == 2


def test_base_and_flavor_aliases_are_separate(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)

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


def test_validation_rejects_lower_scoring_observed_winner(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["judgment_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["queries"][0]["observed_winner"] = "approach-a"
    _write_json(path, artifact)

    with pytest.raises(ValueError, match="easy.*q1.*approach-a"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_requires_explicit_observed_winner_field(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["judgment_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["queries"][0].pop("observed_winner")
    _write_json(path, artifact)

    with pytest.raises(ValueError, match="easy.*q1.*observed_winner"):
        build_leaderboards(datasets, root=tmp_path)


@pytest.mark.parametrize("winner", ["", 0, False])
def test_validation_rejects_malformed_falsy_observed_winner(
    tmp_path: Path, winner: object
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["judgment_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["queries"][0]["observed_winner"] = winner
    _write_json(path, artifact)

    with pytest.raises(ValueError, match="easy.*q1.*nonempty string"):
        build_leaderboards(datasets, root=tmp_path)


def test_missing_flavor_snapshots_for_measured_dataset_fail(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    datasets[0].pop("flavor_evaluation_snapshot")
    datasets[0].pop("flavor_judgment_snapshot")

    with pytest.raises(ValueError, match="'easy'.*flavor_evaluation_snapshot"):
        build_leaderboards(datasets, root=tmp_path)


def test_partial_judge_panel_errors_preserve_valid_scores_and_counts(
    tmp_path: Path,
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    judgment_path = tmp_path / datasets[0]["judgment_snapshot"]
    judgments = json.loads(judgment_path.read_text(encoding="utf-8"))
    judgments["queries"][0]["mean_by_approach"]["approach-a"] = 1.0
    judgments["queries"][0]["per_judge"]["judge-b"] = {
        "error": "no valid verdict"
    }
    _write_json(judgment_path, judgments)
    evaluation_path = tmp_path / datasets[0]["evaluation_snapshot"]
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["datasets"]["easy"]["approaches"]["approach-a"]["judge_panel"][
        "mean"
    ] = 1.0
    _write_json(evaluation_path, evaluation)

    result = build_leaderboards(datasets, root=tmp_path)
    dataset_row = next(
        row for row in result["base"]["by_dataset"]
        if row["dataset"] == "easy" and row["approach"] == "approach-a"
    )
    overall_row = next(
        row for row in result["base"]["overall"] if row["approach"] == "approach-a"
    )

    assert dataset_row["judge_by_model"] == {"judge-a": 1.0, "judge-b": None}
    assert dataset_row["judge_errors"] == 1
    assert dataset_row["judge_disagreement"] is None
    assert overall_row["judge_errors"] == 3
    assert overall_row["judge_by_model"] == {"judge-a": 4.0, "judge-b": 5.0}
    assert overall_row["judge_by_model_evaluated"] == {
        "judge-a": 4,
        "judge-b": 3,
    }


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda summary: summary["judge_panel"].update({"mean": 2.0, "evaluated": 0}),
            "judge mean requires positive evaluated coverage",
        ),
        (
            lambda summary: summary["judge_panel"].update({"mean": float("nan")}),
            "must be finite",
        ),
        (
            lambda summary: summary["operational"].update({"successful": 0}),
            "operational counters",
        ),
        (
            lambda summary: summary["ragas"]["faithfulness"].update({"errors": 1}),
            "Ragas counters",
        ),
        (
            lambda summary: summary["judge_panel"].update({"evaluated": 2}),
            "judge evaluated count",
        ),
    ],
)
def test_validation_rejects_malformed_counts_and_denominators(
    tmp_path: Path,
    mutate: Any,
    message: str,
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["evaluation_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    mutate(artifact["datasets"]["easy"]["approaches"]["approach-a"])
    _write_json(path, artifact)

    with pytest.raises(ValueError, match=message):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_requires_same_approaches_on_all_measured_datasets(
    tmp_path: Path,
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    evaluation_path = tmp_path / datasets[1]["evaluation_snapshot"]
    evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
    evaluation["datasets"]["hard"]["approaches"].pop("approach-b")
    _write_json(evaluation_path, evaluation)
    judgment_path = tmp_path / datasets[1]["judgment_snapshot"]
    judgments = json.loads(judgment_path.read_text(encoding="utf-8"))
    for query in judgments["queries"]:
        query["mean_by_approach"].pop("approach-b", None)
        for detail in query["per_judge"].values():
            if "scores" in detail:
                detail["scores"].pop("approach-b")
    _write_json(judgment_path, judgments)

    with pytest.raises(ValueError, match="hard.*configured base approach set"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_configured_base_approach_omitted_from_every_dataset(
    tmp_path: Path,
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    for dataset in datasets:
        evaluation_path = tmp_path / dataset["evaluation_snapshot"]
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        evaluation["datasets"][dataset["id"]]["approaches"].pop("approach-b")
        _write_json(evaluation_path, evaluation)
        judgment_path = tmp_path / dataset["judgment_snapshot"]
        judgments = json.loads(judgment_path.read_text(encoding="utf-8"))
        for query in judgments["queries"]:
            query["mean_by_approach"].pop("approach-b", None)
            if query["observed_winner"] == "approach-b":
                query["observed_winner"] = "approach-a"
            for detail in query["per_judge"].values():
                if "scores" in detail:
                    detail["scores"].pop("approach-b")
        _write_json(judgment_path, judgments)

    with pytest.raises(ValueError, match="configured base approach set"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_configured_flavor_omitted_from_every_dataset(
    tmp_path: Path,
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    flavors_path = tmp_path / "compare" / "flavors.yaml"
    flavors = yaml.safe_load(flavors_path.read_text(encoding="utf-8"))
    flavors["flavors"].append({"alias": "approach-b-fast", "base": "approach-b"})
    flavors_path.write_text(yaml.safe_dump(flavors), encoding="utf-8")

    with pytest.raises(ValueError, match="configured flavor approach set"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_flavor_with_unconfigured_base_family(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    flavors_path = tmp_path / "compare" / "flavors.yaml"
    flavors = yaml.safe_load(flavors_path.read_text(encoding="utf-8"))
    flavors["flavors"][0]["base"] = "missing-base"
    flavors_path.write_text(yaml.safe_dump(flavors), encoding="utf-8")

    with pytest.raises(ValueError, match="base family.*missing-base.*not configured"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_flavor_alias_that_shadows_base_approach(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    flavors_path = tmp_path / "compare" / "flavors.yaml"
    flavors = yaml.safe_load(flavors_path.read_text(encoding="utf-8"))
    flavors["flavors"][0]["alias"] = "approach-a"
    flavors_path.write_text(yaml.safe_dump(flavors), encoding="utf-8")

    with pytest.raises(ValueError, match="flavor alias.*approach-a.*shadows.*base"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_duplicate_dataset_ids(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    datasets.append(dict(datasets[0]))

    with pytest.raises(ValueError, match="duplicate dataset id.*easy"):
        build_leaderboards(datasets, root=tmp_path)


@pytest.mark.parametrize("dataset_id", ["", None])
def test_validation_rejects_empty_dataset_ids(
    tmp_path: Path, dataset_id: str | None
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    datasets[0]["id"] = dataset_id

    with pytest.raises(ValueError, match="dataset id must be a nonempty string"):
        build_leaderboards(datasets, root=tmp_path)


@pytest.mark.parametrize("metric_name", ["answer_relevancy", "faithfulness"])
def test_validation_rejects_ragas_total_that_differs_from_query_count(
    tmp_path: Path, metric_name: str
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["evaluation_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    metric = artifact["datasets"]["easy"]["approaches"]["approach-a"]["ragas"][metric_name]
    metric.update({"total": 2, "not_evaluable": 1, "coverage": 0.5})
    _write_json(path, artifact)

    with pytest.raises(ValueError, match=f"Ragas {metric_name} total.*judgment queries"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_operational_attempts_that_differ_from_query_count(
    tmp_path: Path,
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["evaluation_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    operational = artifact["datasets"]["easy"]["approaches"]["approach-a"]["operational"]
    operational.update({"attempted": 2, "successful": 2})
    _write_json(path, artifact)

    with pytest.raises(ValueError, match="operational attempted.*judgment queries"):
        build_leaderboards(datasets, root=tmp_path)


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_validation_rejects_ragas_mean_outside_unit_interval(
    tmp_path: Path, value: float
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["evaluation_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["datasets"]["easy"]["approaches"]["approach-a"]["ragas"][
        "faithfulness"
    ]["mean"] = value
    _write_json(path, artifact)

    with pytest.raises(ValueError, match=r"Ragas faithfulness mean.*\[0, 1\]"):
        build_leaderboards(datasets, root=tmp_path)


@pytest.mark.parametrize("value", [0.99, 5.01])
def test_validation_rejects_judge_score_outside_one_to_five(
    tmp_path: Path, value: float
) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["judgment_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    query = artifact["queries"][0]
    query["per_judge"]["judge-a"]["scores"]["approach-a"] = value
    _write_json(path, artifact)

    with pytest.raises(ValueError, match=r"score from judge-a.*\[1, 5\]"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_negative_mean_latency(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    path = tmp_path / datasets[0]["evaluation_snapshot"]
    artifact = json.loads(path.read_text(encoding="utf-8"))
    artifact["datasets"]["easy"]["approaches"]["approach-a"]["operational"][
        "mean_latency_ms"
    ] = -1
    _write_json(path, artifact)

    with pytest.raises(ValueError, match="operational latency mean must be non-negative"):
        build_leaderboards(datasets, root=tmp_path)


def test_validation_rejects_non_positive_complexity_level(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)
    datasets[0]["complexity_level"] = 0

    with pytest.raises(ValueError, match="complexity_level.*positive integer"):
        build_leaderboards(datasets, root=tmp_path)


def test_competition_ranks_preserve_ties() -> None:
    assert competition_ranks(
        {"a": 4.0, "b": 4.0, "c": 3.0}, higher_is_better=True
    ) == {"a": 1, "b": 1, "c": 3}


def test_mean_pairwise_disagreement() -> None:
    assert mean_pairwise_disagreement([[1.0, 3.0], [2.0, 5.0]]) == 2.5
    assert mean_pairwise_disagreement([[4.0]]) is None


def test_means_use_stable_floating_point_summation() -> None:
    cancellation = [1e16, 1.0, -1e16]

    assert _mean(cancellation) == 0.333333
    assert _weighted_mean([(value, 1) for value in cancellation]) == 0.333333


def test_leaderboard_report_contains_all_result_views() -> None:
    report = report_leaderboards.build_report()

    assert "## 2. Overall Base-Approach Leaderboard" in report
    assert 'id="base-overall"' in report
    assert 'id="base-by-dataset"' in report
    assert 'id="flavor-overall"' in report
    assert 'id="flavor-by-dataset"' in report
    assert "Dataset-macro judge" in report
    assert "Query-weighted judge" in report
    assert "Faithfulness coverage" in report
    assert "Errors" in report
    assert "Timeouts" in report


def test_committed_leaderboard_report_is_fresh() -> None:
    assert report_leaderboards.build_report() == (
        ROOT / "docs" / "evaluation-results.md"
    ).read_text(encoding="utf-8")


def test_renderer_escapes_html_and_marks_missing_values_unsortable() -> None:
    table = report_leaderboards.render_table(
        "base-overall",
        [
            report_leaderboards.Column("approach", "Approach", sort_type="text"),
            report_leaderboards.Column("score", "Score"),
        ],
        [{"approach": "<unsafe&>", "score": (None, "N/A")}],
    )

    assert "&lt;unsafe&amp;&gt;" in table
    assert '<td data-sort-value="">N/A</td>' in table


def test_dynamic_judge_columns_are_ordered_by_model_name() -> None:
    columns = report_leaderboards._judge_columns(["judge-z", "judge-a"])

    assert [column.label for column in columns] == [
        "Judge judge-a",
        "Judge judge-a coverage",
        "Judge judge-z",
        "Judge judge-z coverage",
    ]


def test_leaderboard_columns_include_all_independent_metrics() -> None:
    labels = {
        column.label
        for columns in (
            report_leaderboards._overall_columns(["judge-a"], flavors=False),
            report_leaderboards._by_dataset_columns(["judge-a"], flavors=True),
        )
        for column in columns
    }

    assert {
        "Dataset-macro judge",
        "Query-weighted judge",
        "Judge coverage",
        "Judge errors",
        "Judge judge-a",
        "Judge judge-a coverage",
        "Judge disagreement",
        "Answer relevancy coverage (eligible)",
        "Answer relevancy total rows",
        "Answer relevancy ineligible",
        "Answer relevancy errors",
        "Answer relevancy timeouts",
        "Faithfulness coverage (eligible)",
        "Faithfulness total rows",
        "Faithfulness ineligible",
        "Faithfulness errors",
        "Faithfulness timeouts",
        "Mean latency (ms)",
        "Successful",
        "Attempted",
        "Error rate",
        "Errors",
        "Timeouts",
    } <= labels


def test_detailed_rows_include_filter_metadata() -> None:
    table = report_leaderboards.render_table(
        "base-by-dataset",
        [report_leaderboards.Column("approach", "Approach", sort_type="text")],
        [{
            "dataset": "dataset-a",
            "approach": "approach-a",
            "base-family": "base-a",
        }],
    )

    assert 'data-filter-dataset="dataset-a"' in table
    assert 'data-filter-approach="approach-a"' in table
    assert 'data-filter-base-family="base-a"' in table


def test_report_preserves_aggregation_default_ordering() -> None:
    result = build_leaderboards(
        yaml.safe_load((ROOT / "compare" / "datasets.yaml").read_text(encoding="utf-8"))["datasets"]
    )
    expected = [row["approach"] for row in result["base"]["overall"]]
    rows = report_leaderboards._overall_rows(
        result["base"]["overall"], result["base"]["judge_models"]
    )

    assert [row["approach"] for row in rows] == expected


def test_ragas_coverage_uses_eligible_rows_and_keeps_ineligible_rows_visible(
    tmp_path: Path,
) -> None:
    result = build_leaderboards(_write_two_dataset_fixture(tmp_path), root=tmp_path)
    partial = next(
        row for row in report_leaderboards._overall_rows(
            result["base"]["overall"], result["base"]["judge_models"]
        )
        if row["approach"] == "approach-a"
    )
    graph_result = build_leaderboards(
        _write_graph_ineligible_fixture(tmp_path / "graph"), root=tmp_path / "graph"
    )
    graph = report_leaderboards._by_dataset_rows(
        graph_result["base"]["by_dataset"], graph_result["base"]["judge_models"]
    )[0]

    assert partial["faithfulness-coverage"] == (0.75, "3 / 4 (75.00%)")
    assert partial["faithfulness-ineligible"] == 1
    assert graph["faithfulness-coverage"] == (None, "N/A")
    assert graph["faithfulness-ineligible"] == 2


def test_cli_writes_relative_output_from_repo_root_and_creates_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(report_leaderboards, "ROOT", tmp_path)
    monkeypatch.setattr(report_leaderboards, "build_report", lambda: "report\n")
    monkeypatch.setattr(sys, "argv", ["report_leaderboards.py", "--output", "nested/report.md"])

    report_leaderboards.main()

    assert (tmp_path / "nested" / "report.md").read_text(encoding="utf-8") == "report\n"
    assert capsys.readouterr().out == "wrote nested/report.md\n"


def test_cli_writes_absolute_output_outside_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_root = tmp_path / "repo"
    output = tmp_path / "outside" / "report.md"
    monkeypatch.setattr(report_leaderboards, "ROOT", repo_root)
    monkeypatch.setattr(report_leaderboards, "build_report", lambda: "report\n")
    monkeypatch.setattr(sys, "argv", ["report_leaderboards.py", "--output", str(output)])

    report_leaderboards.main()

    assert output.read_text(encoding="utf-8") == "report\n"
    assert capsys.readouterr().out == f"wrote {output}\n"


def test_report_keeps_dataset_ladder_as_a_valid_markdown_link() -> None:
    report = report_leaderboards.build_report()

    assert "[dataset complexity ladder](dataset-complexity-report.md)" in report
    assert "[dataset complexity ladder]\n(dataset-complexity-report.md)" not in report
