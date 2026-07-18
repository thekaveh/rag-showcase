"""Deterministic cross-dataset evaluation leaderboard aggregation."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _weighted_mean(points: list[tuple[float | None, int]]) -> float | None:
    usable = [(value, weight) for value, weight in points if value is not None and weight > 0]
    total = sum(weight for _, weight in usable)
    return round(sum(value * weight for value, weight in usable) / total, 6) if total else None


def competition_ranks(
    values: dict[str, float | None], *, higher_is_better: bool
) -> dict[str, int | None]:
    ranked = [(name, value) for name, value in values.items() if value is not None]
    ranked.sort(key=lambda item: ((-item[1] if higher_is_better else item[1]), item[0]))
    result: dict[str, int | None] = {name: None for name in values}
    previous: float | None = None
    previous_rank = 0
    for index, (name, value) in enumerate(ranked, start=1):
        rank = previous_rank if previous is not None and value == previous else index
        result[name] = rank
        previous = value
        previous_rank = rank
    return result


def mean_pairwise_disagreement(scores: list[list[float]]) -> float | None:
    differences: list[float] = []
    for query_scores in scores:
        for left in range(len(query_scores)):
            for right in range(left + 1, len(query_scores)):
                differences.append(abs(query_scores[left] - query_scores[right]))
    return round(sum(differences) / len(differences), 6) if differences else None


def _load_json(root: Path, path: str, *, description: str) -> dict[str, Any]:
    snapshot = root / path
    try:
        loaded = json.loads(snapshot.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load {description} snapshot {snapshot}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{description} snapshot {snapshot} must contain an object")
    return loaded


def _flavor_bases(root: Path) -> dict[str, str]:
    manifest = root / "compare" / "flavors.yaml"
    if not manifest.is_file():
        return {}
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"cannot load flavor manifest {manifest}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("flavors", []), list):
        raise ValueError(f"flavor manifest {manifest} must contain a flavors list")
    bases: dict[str, str] = {}
    for index, row in enumerate(data["flavors"]):
        if not isinstance(row, dict) or not row.get("alias") or not row.get("base"):
            raise ValueError(f"flavor manifest entry {index} must contain alias and base")
        alias, base = str(row["alias"]), str(row["base"])
        if alias in bases:
            raise ValueError(f"flavor manifest contains duplicate alias {alias!r}")
        bases[alias] = base
    return bases


def _snapshot_paths(dataset: dict[str, Any], *, tier: str) -> tuple[str, str] | None:
    if tier == "base":
        keys = ("evaluation_snapshot", "judgment_snapshot")
    else:
        keys = ("flavor_evaluation_snapshot", "flavor_judgment_snapshot")
    evaluation, judgment = (dataset.get(key) for key in keys)
    if evaluation is None and judgment is None and tier == "flavors":
        return None
    if not evaluation or not judgment:
        raise ValueError(
            f"measured dataset {dataset.get('id')!r} requires both {keys[0]} and {keys[1]}"
        )
    return str(evaluation), str(judgment)


def _metric(summary: dict[str, Any], name: str) -> dict[str, Any]:
    ragas = summary.get("ragas")
    if not isinstance(ragas, dict) or not isinstance(ragas.get(name), dict):
        raise ValueError(f"approach summary is missing Ragas metric {name!r}")
    metric = ragas[name]
    required = ("mean", "evaluated", "total", "not_evaluable", "errors", "timeouts")
    if any(key not in metric for key in required):
        raise ValueError(f"Ragas metric {name!r} is missing coverage counters")
    return metric


def _rankings(summary: dict[str, Any], approaches: dict[str, dict[str, Any]]) -> dict[str, dict[str, int | None]]:
    return {
        "judge": competition_ranks(
            {name: values["judge_panel"]["mean"] for name, values in approaches.items()},
            higher_is_better=True,
        ),
        "answer_relevancy": competition_ranks(
            {name: _metric(values, "answer_relevancy")["mean"] for name, values in approaches.items()},
            higher_is_better=True,
        ),
        "faithfulness": competition_ranks(
            {name: _metric(values, "faithfulness")["mean"] for name, values in approaches.items()},
            higher_is_better=True,
        ),
        "latency": competition_ranks(
            {name: values["operational"]["mean_latency_ms"] for name, values in approaches.items()},
            higher_is_better=False,
        ),
    }


def _judge_details(
    judgments: dict[str, Any], approaches: set[str], dataset_id: str
) -> tuple[dict[str, dict[str, float | None]], dict[str, float | None], dict[str, int], list[str]]:
    if judgments.get("dataset_id") != dataset_id:
        raise ValueError(f"judgment snapshot must identify dataset {dataset_id!r}")
    queries = judgments.get("queries")
    if not isinstance(queries, list):
        raise ValueError(f"judgment snapshot for {dataset_id!r} must contain a queries list")
    models = judgments.get("judges", [])
    if not isinstance(models, list) or not all(isinstance(model, str) for model in models):
        raise ValueError(f"judgment snapshot for {dataset_id!r} has invalid judges")
    model_scores: dict[str, dict[str, list[float]]] = {
        approach: {model: [] for model in models} for approach in approaches
    }
    disagreement_scores: dict[str, list[list[float]]] = {approach: [] for approach in approaches}
    winners = {approach: 0 for approach in approaches}
    for index, query in enumerate(queries):
        if not isinstance(query, dict) or "mean_by_approach" not in query:
            raise ValueError(
                f"judgment query {index} for {dataset_id!r} must contain mean_by_approach"
            )
        means = query["mean_by_approach"]
        if not isinstance(means, dict) or set(means) != approaches:
            raise ValueError(
                f"judgment query {index} approaches do not match evaluation approaches"
            )
        per_judge = query.get("per_judge")
        if not isinstance(per_judge, dict):
            raise ValueError(f"judgment query {index} for {dataset_id!r} has invalid per_judge")
        if set(per_judge) != set(models):
            raise ValueError(
                f"judgment query {index} judge coverage does not match the panel"
            )
        for approach, value in means.items():
            try:
                float(value)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"judgment query {index} has non-numeric score") from exc
        for model, detail in per_judge.items():
            if not isinstance(model, str) or not isinstance(detail, dict):
                raise ValueError(f"judgment query {index} has invalid per-judge result")
            scores = detail.get("scores")
            if not isinstance(scores, dict) or set(scores) != approaches:
                raise ValueError(
                    f"judgment query {index} per-judge approaches do not match evaluation approaches"
                )
            for approach, value in scores.items():
                try:
                    model_scores[approach][model].append(float(value))
                except (TypeError, ValueError) as exc:
                    raise ValueError(f"judgment query {index} has non-numeric per-judge score") from exc
        for approach in approaches:
            values = [scores[approach] for scores in (
                detail["scores"] for detail in per_judge.values()
            )]
            disagreement_scores[approach].append([float(value) for value in values])
        winner = query.get("observed_winner")
        if winner is not None:
            if winner not in approaches:
                raise ValueError(f"judgment query {index} names an unknown observed winner")
            winners[winner] += 1
    by_model = {
        approach: {model: _mean(scores) for model, scores in model_scores[approach].items()}
        for approach in approaches
    }
    disagreement = {
        approach: mean_pairwise_disagreement(values)
        for approach, values in disagreement_scores.items()
    }
    return by_model, disagreement, winners, sorted(set(models))


def _records_for_dataset(
    dataset: dict[str, Any],
    evaluation: dict[str, Any],
    judgments: dict[str, Any],
    *,
    flavor_bases: dict[str, str],
    tier: str,
) -> tuple[list[dict[str, Any]], list[str]]:
    dataset_id = str(dataset.get("id") or "")
    datasets = evaluation.get("datasets")
    if not isinstance(datasets, dict) or set(datasets) != {dataset_id}:
        raise ValueError(f"evaluation snapshot must contain exactly dataset {dataset_id!r}")
    scope = datasets[dataset_id]
    if not isinstance(scope, dict) or not isinstance(scope.get("approaches"), dict):
        raise ValueError(f"evaluation snapshot for {dataset_id!r} must contain approaches")
    approaches = scope["approaches"]
    if not approaches:
        raise ValueError(f"evaluation snapshot for {dataset_id!r} has no approaches")
    approach_names = set(approaches)
    if tier == "base" and approach_names & set(flavor_bases):
        raise ValueError(f"base snapshot for {dataset_id!r} contains flavor aliases")
    if tier == "flavors" and not approach_names <= set(flavor_bases):
        raise ValueError(f"flavor snapshot for {dataset_id!r} contains unknown flavor aliases")
    for approach, summary in approaches.items():
        if not isinstance(summary, dict) or not isinstance(summary.get("judge_panel"), dict):
            raise ValueError(f"approach {approach!r} is missing judge panel summary")
        if not isinstance(summary.get("operational"), dict):
            raise ValueError(f"approach {approach!r} is missing operational summary")
        judge = summary["judge_panel"]
        operational = summary["operational"]
        if any(key not in judge for key in ("mean", "evaluated", "total")):
            raise ValueError(f"approach {approach!r} has incomplete judge coverage")
        if any(key not in operational for key in ("attempted", "successful", "errors", "timeouts", "mean_latency_ms")):
            raise ValueError(f"approach {approach!r} has incomplete operational coverage")
        _metric(summary, "answer_relevancy")
        _metric(summary, "faithfulness")
    judge_by_model, disagreement, wins, models = _judge_details(
        judgments, approach_names, dataset_id
    )
    ranks = _rankings(scope, approaches)
    records = []
    for approach in sorted(approaches):
        summary = approaches[approach]
        base_family = flavor_bases.get(approach, approach)
        records.append(
            {
                "dataset": dataset_id,
                "complexity": int(dataset["complexity_level"]),
                "approach": approach,
                "base_family": base_family,
                "maturity": "experimental" if base_family == "lazy-graph-rag" else "canonical",
                "judge_rank": ranks["judge"][approach],
                "judge_mean": summary["judge_panel"]["mean"],
                "judge_evaluated": int(summary["judge_panel"]["evaluated"]),
                "judge_total": int(summary["judge_panel"]["total"]),
                "judge_by_model": judge_by_model[approach],
                "judge_disagreement": disagreement[approach],
                "answer_relevancy_rank": ranks["answer_relevancy"][approach],
                "answer_relevancy": _metric(summary, "answer_relevancy"),
                "faithfulness_rank": ranks["faithfulness"][approach],
                "faithfulness": _metric(summary, "faithfulness"),
                "latency_rank": ranks["latency"][approach],
                "operational": summary["operational"],
                "query_wins": wins[approach],
            }
        )
    return records, models


def _overall_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_approach: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_approach.setdefault(row["approach"], []).append(row)
    output: list[dict[str, Any]] = []
    for approach, values in by_approach.items():
        answer = [row["answer_relevancy"] for row in values]
        faithfulness = [row["faithfulness"] for row in values]
        operational = [row["operational"] for row in values]
        judge_models = sorted({model for row in values for model in row["judge_by_model"]})
        judge_by_model = {
            model: _weighted_mean([
                (row["judge_by_model"].get(model), row["judge_evaluated"])
                for row in values
            ])
            for model in judge_models
        }
        output.append(
            {
                "approach": approach,
                "base_family": values[0]["base_family"],
                "maturity": values[0]["maturity"],
                "judge_macro_mean": _mean([
                    float(row["judge_mean"]) for row in values if row["judge_mean"] is not None
                ]),
                "judge_weighted_mean": _weighted_mean([
                    (row["judge_mean"], row["judge_evaluated"]) for row in values
                ]),
                "judge_evaluated": sum(row["judge_evaluated"] for row in values),
                "judge_total": sum(row["judge_total"] for row in values),
                "judge_by_model": judge_by_model,
                "judge_disagreement": _weighted_mean([
                    (row["judge_disagreement"], row["judge_evaluated"]) for row in values
                ]),
                "mean_dataset_rank": _mean([
                    float(row["judge_rank"]) for row in values if row["judge_rank"] is not None
                ]),
                "best_dataset_rank": min(
                    (row["judge_rank"] for row in values if row["judge_rank"] is not None),
                    default=None,
                ),
                "worst_dataset_rank": max(
                    (row["judge_rank"] for row in values if row["judge_rank"] is not None),
                    default=None,
                ),
                "query_wins": sum(row["query_wins"] for row in values),
                "answer_relevancy_mean": _weighted_mean([
                    (metric["mean"], int(metric["evaluated"])) for metric in answer
                ]),
                "answer_relevancy_evaluated": sum(int(metric["evaluated"]) for metric in answer),
                "answer_relevancy_total": sum(int(metric["total"]) for metric in answer),
                "answer_relevancy_not_evaluable": sum(int(metric["not_evaluable"]) for metric in answer),
                "answer_relevancy_errors": sum(int(metric["errors"]) for metric in answer),
                "answer_relevancy_timeouts": sum(int(metric["timeouts"]) for metric in answer),
                "faithfulness_mean": _weighted_mean([
                    (metric["mean"], int(metric["evaluated"])) for metric in faithfulness
                ]),
                "faithfulness_evaluated": sum(int(metric["evaluated"]) for metric in faithfulness),
                "faithfulness_total": sum(int(metric["total"]) for metric in faithfulness),
                "faithfulness_not_evaluable": sum(int(metric["not_evaluable"]) for metric in faithfulness),
                "faithfulness_errors": sum(int(metric["errors"]) for metric in faithfulness),
                "faithfulness_timeouts": sum(int(metric["timeouts"]) for metric in faithfulness),
                "mean_latency_ms": _weighted_mean([
                    (metric["mean_latency_ms"], int(metric["successful"])) for metric in operational
                ]),
                "successful": sum(int(metric["successful"]) for metric in operational),
                "attempted": sum(int(metric["attempted"]) for metric in operational),
                "errors": sum(int(metric["errors"]) for metric in operational),
                "timeouts": sum(int(metric["timeouts"]) for metric in operational),
            }
        )
    ranks = competition_ranks(
        {row["approach"]: row["judge_macro_mean"] for row in output},
        higher_is_better=True,
    )
    for row in output:
        row["overall_rank"] = ranks[row["approach"]]
        failures = row["errors"] + row["timeouts"]
        row["error_rate"] = round(failures / row["attempted"], 6) if row["attempted"] else None
    return sorted(
        output,
        key=lambda row: (
            row["overall_rank"] is None,
            row["overall_rank"] if row["overall_rank"] is not None else 0,
            row["approach"],
        ),
    )


def _tier(datasets: list[dict[str, Any]], *, root: Path, tier: str, flavor_bases: dict[str, str]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    models: set[str] = set()
    covered_datasets: set[str] = set()
    for dataset in sorted(datasets, key=lambda row: (int(row["complexity_level"]), str(row["id"]))):
        if dataset.get("status") != "measured":
            continue
        paths = _snapshot_paths(dataset, tier=tier)
        if paths is None:
            continue
        evaluation_path, judgment_path = paths
        records, tier_models = _records_for_dataset(
            dataset,
            _load_json(root, evaluation_path, description="evaluation"),
            _load_json(root, judgment_path, description="judgment"),
            flavor_bases=flavor_bases,
            tier=tier,
        )
        rows.extend(records)
        models.update(tier_models)
        covered_datasets.add(str(dataset["id"]))
    by_dataset = sorted(
        rows,
        key=lambda row: (
            row["complexity"],
            row["dataset"],
            row["judge_rank"] is None,
            row["judge_rank"] if row["judge_rank"] is not None else 0,
            row["approach"],
        ),
    )
    return {
        "overall": _overall_records(rows),
        "by_dataset": by_dataset,
        "judge_models": sorted(models),
        "dataset_count": len(covered_datasets),
    }


def build_leaderboards(
    datasets: list[dict[str, Any]], *, root: Path = ROOT
) -> dict[str, Any]:
    """Build isolated base and flavor leaderboards from measured snapshots."""
    flavor_bases = _flavor_bases(root)
    return {
        "base": _tier(datasets, root=root, tier="base", flavor_bases=flavor_bases),
        "flavors": _tier(datasets, root=root, tier="flavors", flavor_bases=flavor_bases),
    }
