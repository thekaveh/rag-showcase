"""Deterministic cross-dataset evaluation leaderboard aggregation."""
from __future__ import annotations

import json
import math
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


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be numeric")
    numeric = float(value)
    if not math.isfinite(numeric):
        raise ValueError(f"{label} must be finite")
    return numeric


def _bounded(value: Any, label: str, minimum: float, maximum: float) -> float:
    numeric = _finite(value, label)
    if not minimum <= numeric <= maximum:
        raise ValueError(f"{label} must be within [{minimum:g}, {maximum:g}]")
    return numeric


def _counter(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer")
    return value


def _positive_integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return value


def _mean_with_coverage(value: Any, evaluated: int, label: str) -> float | None:
    if value is None:
        if evaluated:
            raise ValueError(f"{label} mean is missing with evaluated coverage")
        return None
    numeric = _finite(value, f"{label} mean")
    if not evaluated:
        raise ValueError(f"{label} mean requires positive evaluated coverage")
    return numeric


def _coverage(value: Any, evaluated: int, total: int, label: str) -> None:
    expected = round(evaluated / total, 6) if total else 0.0
    if _finite(value, f"{label} coverage") != expected:
        raise ValueError(f"{label} coverage does not match evaluated and total")


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


def _base_approaches(root: Path) -> set[str]:
    manifest = root / "compare" / "evaluation.yaml"
    try:
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"cannot load evaluation manifest {manifest}: {exc}") from exc
    rows = data.get("approaches") if isinstance(data, dict) else None
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"evaluation manifest {manifest} must contain an approaches list")
    approaches: set[str] = set()
    for index, row in enumerate(rows):
        model = row.get("model") if isinstance(row, dict) else None
        if not isinstance(model, str) or not model:
            raise ValueError(f"evaluation manifest approach {index} must contain a model")
        if model in approaches:
            raise ValueError(f"evaluation manifest contains duplicate approach {model!r}")
        approaches.add(model)
    return approaches


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


def _snapshot_paths(dataset: dict[str, Any], *, tier: str) -> tuple[str, str]:
    keys = (
        ("evaluation_snapshot", "judgment_snapshot")
        if tier == "base"
        else ("flavor_evaluation_snapshot", "flavor_judgment_snapshot")
    )
    evaluation, judgment = (dataset.get(key) for key in keys)
    if not evaluation or not judgment:
        raise ValueError(
            f"measured dataset {dataset.get('id')!r} requires both {keys[0]} and {keys[1]}"
        )
    return str(evaluation), str(judgment)


def _validate_dataset_ids(datasets: list[dict[str, Any]]) -> None:
    ids: list[str] = []
    for dataset in datasets:
        dataset_id = dataset.get("id") if isinstance(dataset, dict) else None
        if not isinstance(dataset_id, str) or not dataset_id.strip():
            raise ValueError("dataset id must be a nonempty string")
        ids.append(dataset_id)
    duplicates = sorted({dataset_id for dataset_id in ids if ids.count(dataset_id) > 1})
    if duplicates:
        raise ValueError(f"duplicate dataset id(s): {', '.join(duplicates)}")


def _metric(summary: dict[str, Any], name: str) -> dict[str, Any]:
    ragas = summary.get("ragas")
    if not isinstance(ragas, dict) or not isinstance(ragas.get(name), dict):
        raise ValueError(f"approach summary is missing Ragas metric {name!r}")
    metric = ragas[name]
    required = (
        "mean", "evaluated", "total", "not_evaluable", "errors", "timeouts", "coverage"
    )
    if any(key not in metric for key in required):
        raise ValueError(f"Ragas metric {name!r} is missing coverage counters")
    evaluated = _counter(metric["evaluated"], f"Ragas {name} evaluated")
    total = _counter(metric["total"], f"Ragas {name} total")
    not_evaluable = _counter(metric["not_evaluable"], f"Ragas {name} not_evaluable")
    errors = _counter(metric["errors"], f"Ragas {name} errors")
    timeouts = _counter(metric["timeouts"], f"Ragas {name} timeouts")
    if evaluated > total:
        raise ValueError(f"Ragas {name} evaluated count exceeds total")
    if evaluated + not_evaluable + errors + timeouts != total:
        raise ValueError(f"Ragas counters for {name} do not add up to total")
    mean = _mean_with_coverage(metric["mean"], evaluated, f"Ragas {name}")
    if mean is not None:
        _bounded(mean, f"Ragas {name} mean", 0, 1)
    _coverage(metric["coverage"], evaluated, total, f"Ragas {name}")
    return metric


def _validate_operational(summary: dict[str, Any]) -> dict[str, Any]:
    operational = summary.get("operational")
    if not isinstance(operational, dict):
        raise ValueError("approach summary is missing operational summary")
    required = ("attempted", "successful", "errors", "timeouts", "mean_latency_ms", "error_rate")
    if any(key not in operational for key in required):
        raise ValueError("approach summary has incomplete operational coverage")
    attempted = _counter(operational["attempted"], "operational attempted")
    successful = _counter(operational["successful"], "operational successful")
    errors = _counter(operational["errors"], "operational errors")
    timeouts = _counter(operational["timeouts"], "operational timeouts")
    if successful + errors + timeouts != attempted:
        raise ValueError("operational counters do not add up to attempted")
    mean_latency = _mean_with_coverage(
        operational["mean_latency_ms"], successful, "operational latency"
    )
    if mean_latency is not None and mean_latency < 0:
        raise ValueError("operational latency mean must be non-negative")
    expected_rate = round((errors + timeouts) / attempted, 6) if attempted else 0.0
    if _finite(operational["error_rate"], "operational error_rate") != expected_rate:
        raise ValueError("operational error_rate does not match response counters")
    return operational


def _rankings(approaches: dict[str, dict[str, Any]]) -> dict[str, dict[str, int | None]]:
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
) -> tuple[
    dict[str, dict[str, float | None]],
    dict[str, dict[str, int]],
    dict[str, float | None],
    dict[str, int],
    dict[str, int],
    dict[str, list[float]],
    int,
    list[str],
    int,
]:
    if judgments.get("dataset_id") != dataset_id:
        raise ValueError(f"judgment snapshot must identify dataset {dataset_id!r}")
    queries = judgments.get("queries")
    if not isinstance(queries, list):
        raise ValueError(f"judgment snapshot for {dataset_id!r} must contain a queries list")
    models = judgments.get("judges", [])
    if (
        not isinstance(models, list)
        or not all(isinstance(model, str) for model in models)
        or len(set(models)) != len(models)
    ):
        raise ValueError(f"judgment snapshot for {dataset_id!r} has invalid judges")
    model_scores: dict[str, dict[str, list[float]]] = {
        approach: {model: [] for model in models} for approach in approaches
    }
    disagreement_scores: dict[str, list[list[float]]] = {approach: [] for approach in approaches}
    disagreement_counts = {approach: 0 for approach in approaches}
    winners = {approach: 0 for approach in approaches}
    mean_scores = {approach: [] for approach in approaches}
    judge_errors = 0
    for index, query in enumerate(queries):
        if not isinstance(query, dict) or "mean_by_approach" not in query:
            raise ValueError(
                f"judgment query {index} for {dataset_id!r} must contain mean_by_approach"
            )
        means = query["mean_by_approach"]
        if not isinstance(means, dict) or (means and set(means) != approaches):
            raise ValueError(
                f"judgment query {index} approaches do not match evaluation approaches"
            )
        for approach, value in means.items():
            _bounded(value, f"judgment query {index} score for {approach}", 1, 5)
        per_judge = query.get("per_judge")
        if not isinstance(per_judge, dict) or set(per_judge) != set(models):
            raise ValueError(f"judgment query {index} judge coverage does not match the panel")
        scores_by_approach = {approach: [] for approach in approaches}
        for model, detail in per_judge.items():
            if not isinstance(detail, dict):
                raise ValueError(f"judgment query {index} has invalid per-judge result")
            if "error" in detail:
                if not detail["error"]:
                    raise ValueError(f"judgment query {index} has an empty judge error")
                judge_errors += 1
                continue
            scores = detail.get("scores")
            if not isinstance(scores, dict) or set(scores) != approaches:
                raise ValueError(
                    f"judgment query {index} per-judge approaches do not match evaluation approaches"
                )
            for approach, value in scores.items():
                numeric = _bounded(
                    value, f"judgment query {index} score from {model}", 1, 5
                )
                model_scores[approach][model].append(numeric)
                scores_by_approach[approach].append(numeric)
        if scores_by_approach[next(iter(approaches))] if approaches else False:
            if set(means) != approaches:
                raise ValueError(f"judgment query {index} is missing valid mean scores")
            for approach, scores in scores_by_approach.items():
                expected = round(sum(scores) / len(scores), 2)
                if _finite(means[approach], f"judgment query {index} mean") != expected:
                    raise ValueError(f"judgment query {index} mean_by_approach disagrees with panel")
                mean_scores[approach].append(float(means[approach]))
                disagreement_scores[approach].append(scores)
                disagreement_counts[approach] += len(scores) * (len(scores) - 1) // 2
        elif means:
            raise ValueError(f"judgment query {index} has means without valid judge scores")
        query_id = str(query.get("query_id") or index)
        if "observed_winner" not in query:
            raise ValueError(
                f"judgment dataset {dataset_id!r} query {query_id!r} "
                "is missing observed_winner"
            )
        winner = query.get("observed_winner")
        if winner is not None:
            if not isinstance(winner, str) or not winner:
                raise ValueError(
                    f"judgment dataset {dataset_id!r} query {query_id!r} "
                    "observed_winner must be a nonempty string"
                )
            if winner not in means:
                raise ValueError(
                    f"judgment dataset {dataset_id!r} query {query_id!r} "
                    f"observed_winner {winner!r} is absent from mean_by_approach"
                )
            winner_score = _finite(
                means[winner],
                f"judgment dataset {dataset_id!r} query {query_id!r} winner score",
            )
            highest_score = max(
                _finite(score, f"judgment query {index} mean")
                for score in means.values()
            )
            if winner_score != highest_score:
                raise ValueError(
                    f"judgment dataset {dataset_id!r} query {query_id!r} "
                    f"observed_winner {winner!r} is not in the top-score tie group"
                )
            winners[winner] += 1
    by_model = {
        approach: {model: _mean(scores) for model, scores in model_scores[approach].items()}
        for approach in approaches
    }
    model_evaluated = {
        approach: {model: len(scores) for model, scores in model_scores[approach].items()}
        for approach in approaches
    }
    disagreement = {
        approach: mean_pairwise_disagreement(values)
        for approach, values in disagreement_scores.items()
    }
    return (
        by_model,
        model_evaluated,
        disagreement,
        disagreement_counts,
        winners,
        mean_scores,
        judge_errors,
        sorted(models),
        len(queries),
    )


def _validate_judge_summary(
    summary: dict[str, Any], *, scores: list[float], query_count: int
) -> None:
    judge = summary.get("judge_panel")
    if not isinstance(judge, dict) or any(
        key not in judge for key in ("mean", "evaluated", "total", "coverage")
    ):
        raise ValueError("approach summary has incomplete judge coverage")
    evaluated = _counter(judge["evaluated"], "judge evaluated")
    total = _counter(judge["total"], "judge total")
    if evaluated > total:
        raise ValueError("judge evaluated count exceeds total")
    if total != query_count:
        raise ValueError("judge total count does not match judgment queries")
    mean = _mean_with_coverage(judge["mean"], evaluated, "judge")
    if mean is not None:
        _bounded(mean, "judge mean", 1, 5)
    _coverage(judge["coverage"], evaluated, total, "judge")
    if evaluated != len(scores):
        raise ValueError("judge evaluated count does not match judgment scores")
    if mean != _mean(scores):
        raise ValueError("judge mean does not match judgment scores")


def _records_for_dataset(
    dataset: dict[str, Any],
    evaluation: dict[str, Any],
    judgments: dict[str, Any],
    *,
    configured_approaches: set[str],
    flavor_bases: dict[str, str],
    tier: str,
) -> tuple[list[dict[str, Any]], list[str], set[str]]:
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
    if approach_names != configured_approaches:
        label = "base" if tier == "base" else "flavor"
        missing = sorted(configured_approaches - approach_names)
        unexpected = sorted(approach_names - configured_approaches)
        raise ValueError(
            f"{label} snapshot for dataset {dataset_id!r} does not match configured "
            f"{label} approach set; missing={missing}, unexpected={unexpected}"
        )
    for approach, summary in approaches.items():
        if not isinstance(summary, dict):
            raise ValueError(f"approach {approach!r} has invalid summary")
        _metric(summary, "answer_relevancy")
        _metric(summary, "faithfulness")
        _validate_operational(summary)
    (
        judge_by_model,
        judge_by_model_evaluated,
        disagreement,
        disagreement_evaluated,
        wins,
        mean_scores,
        judge_errors,
        models,
        query_count,
    ) = _judge_details(judgments, approach_names, dataset_id)
    for approach, summary in approaches.items():
        _validate_judge_summary(summary, scores=mean_scores[approach], query_count=query_count)
        for name in ("answer_relevancy", "faithfulness"):
            if _counter(_metric(summary, name)["total"], f"Ragas {name} total") != query_count:
                raise ValueError(f"Ragas {name} total does not match judgment queries")
        if (
            _counter(summary["operational"]["attempted"], "operational attempted")
            != query_count
        ):
            raise ValueError("operational attempted count does not match judgment queries")
    ranks = _rankings(approaches)
    records = []
    for approach in sorted(approaches):
        summary = approaches[approach]
        base_family = flavor_bases.get(approach, approach)
        records.append(
            {
                "dataset": dataset_id,
                "complexity": _positive_integer(
                    dataset.get("complexity_level"), "dataset complexity_level"
                ),
                "approach": approach,
                "base_family": base_family,
                "maturity": "experimental" if base_family == "lazy-graph-rag" else "canonical",
                "judge_rank": ranks["judge"][approach],
                "judge_mean": summary["judge_panel"]["mean"],
                "judge_evaluated": int(summary["judge_panel"]["evaluated"]),
                "judge_total": int(summary["judge_panel"]["total"]),
                "judge_errors": judge_errors,
                "judge_by_model": judge_by_model[approach],
                "judge_by_model_evaluated": judge_by_model_evaluated[approach],
                "judge_disagreement": disagreement[approach],
                "judge_disagreement_evaluated": disagreement_evaluated[approach],
                "answer_relevancy_rank": ranks["answer_relevancy"][approach],
                "answer_relevancy": _metric(summary, "answer_relevancy"),
                "faithfulness_rank": ranks["faithfulness"][approach],
                "faithfulness": _metric(summary, "faithfulness"),
                "latency_rank": ranks["latency"][approach],
                "operational": summary["operational"],
                "query_wins": wins[approach],
            }
        )
    return records, models, approach_names


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
        judge_by_model_evaluated = {
            model: sum(row["judge_by_model_evaluated"].get(model, 0) for row in values)
            for model in judge_models
        }
        judge_by_model = {
            model: _weighted_mean([
                (row["judge_by_model"].get(model), row["judge_by_model_evaluated"].get(model, 0))
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
                "judge_errors": sum(row["judge_errors"] for row in values),
                "judge_by_model": judge_by_model,
                "judge_by_model_evaluated": judge_by_model_evaluated,
                "judge_disagreement": _weighted_mean([
                    (row["judge_disagreement"], row["judge_disagreement_evaluated"])
                    for row in values
                ]),
                "judge_disagreement_evaluated": sum(
                    row["judge_disagreement_evaluated"] for row in values
                ),
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


def _tier(
    datasets: list[dict[str, Any]],
    *,
    root: Path,
    tier: str,
    configured_approaches: set[str],
    flavor_bases: dict[str, str],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    models: set[str] = set()
    for dataset in sorted(
        datasets,
        key=lambda row: (
            _positive_integer(row.get("complexity_level"), "dataset complexity_level"),
            str(row["id"]),
        ),
    ):
        if dataset.get("status") != "measured":
            continue
        evaluation_path, judgment_path = _snapshot_paths(dataset, tier=tier)
        records, tier_models, approach_names = _records_for_dataset(
            dataset,
            _load_json(root, evaluation_path, description="evaluation"),
            _load_json(root, judgment_path, description="judgment"),
            configured_approaches=configured_approaches,
            flavor_bases=flavor_bases,
            tier=tier,
        )
        rows.extend(records)
        models.update(tier_models)
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
        "dataset_count": sum(dataset.get("status") == "measured" for dataset in datasets),
    }


def build_leaderboards(
    datasets: list[dict[str, Any]], *, root: Path = ROOT
) -> dict[str, Any]:
    """Build isolated base and flavor leaderboards from measured snapshots."""
    _validate_dataset_ids(datasets)
    for dataset in datasets:
        if dataset.get("status") == "measured":
            _snapshot_paths(dataset, tier="base")
            _snapshot_paths(dataset, tier="flavors")
    base_approaches = _base_approaches(root)
    flavor_bases = _flavor_bases(root)
    shadowed_aliases = sorted(set(flavor_bases) & base_approaches)
    if shadowed_aliases:
        raise ValueError(
            f"flavor alias {shadowed_aliases[0]!r} shadows a configured base approach"
        )
    unknown_bases = sorted(set(flavor_bases.values()) - base_approaches)
    if unknown_bases:
        raise ValueError(
            f"flavor base family {unknown_bases[0]!r} is not configured as a base approach"
        )
    return {
        "base": _tier(
            datasets,
            root=root,
            tier="base",
            configured_approaches=base_approaches,
            flavor_bases=flavor_bases,
        ),
        "flavors": _tier(
            datasets,
            root=root,
            tier="flavors",
            configured_approaches=set(flavor_bases),
            flavor_bases=flavor_bases,
        ),
    }
