"""Deterministic, coverage-aware summaries derived from canonical evidence rows."""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from compare.evaluation import JsonlStore


def _round(value: float) -> float:
    return round(value, 6)


def _mean(values: list[float]) -> float | None:
    return _round(sum(values) / len(values)) if values else None


def _ranking(
    values: dict[str, float | None],
    coverage: dict[str, dict[str, int]],
    *,
    higher_is_better: bool,
) -> list[dict[str, Any]]:
    eligible = [(name, value) for name, value in values.items() if value is not None]
    eligible.sort(key=lambda item: ((-item[1] if higher_is_better else item[1]), item[0]))
    result: list[dict[str, Any]] = []
    index = 0
    while index < len(eligible):
        value = eligible[index][1]
        names = []
        end = index
        while end < len(eligible) and eligible[end][1] == value:
            names.append(eligible[end][0])
            end += 1
        result.append(
            {
                "rank": index + 1,
                "approaches": sorted(names),
                "value": value,
                "coverage": {name: coverage[name] for name in sorted(names)},
            }
        )
        index = end
    return result


def _judge_scores(
    judgments: dict[str, Any] | None, dataset_ids: list[str]
) -> tuple[
    dict[str, dict[str, list[float]]],
    dict[str, set[tuple[str, str]]],
    dict[str, Any],
]:
    scores: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    evaluated_queries: dict[str, set[tuple[str, str]]] = defaultdict(set)
    if judgments is None:
        return scores, evaluated_queries, {"status": "not_supplied", "models": []}
    raw_models = judgments.get("judges", [])
    models = [str(model) for model in raw_models] if isinstance(raw_models, list) else []

    def invalid(message: str) -> tuple[
        dict[str, dict[str, list[float]]],
        dict[str, set[tuple[str, str]]],
        dict[str, Any],
    ]:
        scores.clear()
        evaluated_queries.clear()
        return scores, evaluated_queries, {
            "status": "error",
            "models": models,
            "error": message,
        }

    if judgments.get("status") == "error":
        return invalid(
            str(judgments.get("error") or "judgment artifact is invalid")
        )
    if judgments.get("status") == "disabled":
        return (
            scores,
            evaluated_queries,
            {"status": "disabled", "models": models},
        )

    dataset_id = judgments.get("dataset_id")
    if not dataset_id:
        dataset_id = dataset_ids[0] if len(dataset_ids) == 1 else None
    if not dataset_id or dataset_id not in dataset_ids:
        return invalid(
            "judgment dataset_id is missing or does not match canonical rows"
        )
    queries = judgments.get("queries", [])
    if not isinstance(queries, list):
        return invalid("judgment queries must be a list")
    for index, query in enumerate(queries):
        if not isinstance(query, dict):
            return invalid(f"judgment query at index {index} must be an object")
        query_scores = query.get("mean_by_approach") or {}
        if not isinstance(query_scores, dict):
            return invalid(
                f"judgment query at index {index} mean_by_approach must be an object"
            )
        if query_scores:
            evaluated_queries[dataset_id].add((dataset_id, str(query.get("query_id") or "")))
        for approach, value in query_scores.items():
            try:
                scores[dataset_id][str(approach)].append(float(value))
            except (TypeError, ValueError):
                return invalid(
                    f"judgment query at index {index} has a non-numeric score"
                )
    status = "ok" if any(scores[dataset_id].values()) else "error"
    return (
        scores,
        evaluated_queries,
        {"status": status, "models": models},
    )


def _scope_summary(
    rows: list[dict[str, Any]],
    *,
    judge_values: dict[str, list[float]],
    judge_evaluated_queries: set[tuple[str, str]],
    judge_meta: dict[str, Any],
) -> dict[str, Any]:
    approaches = sorted({row["approach"]["model"] for row in rows})
    metrics = sorted(
        {
            str(metric)
            for row in rows
            for metric in (row.get("metrics", {}).get("ragas", {}).get("requested") or [])
        }
        | {
            str(metric)
            for row in rows
            for metric in (row.get("metrics", {}).get("ragas", {}).get("scores") or {})
        }
    )
    by_approach = {
        approach: [row for row in rows if row["approach"]["model"] == approach]
        for approach in approaches
    }
    approach_summaries: dict[str, Any] = {}
    for approach, approach_rows in by_approach.items():
        successful = [row for row in approach_rows if row.get("status") == "ok"]
        latencies = [
            float(row["metrics"]["operational"]["latency_ms"])
            for row in successful
        ]
        errors = sum(row.get("status") == "error" for row in approach_rows)
        timeouts = sum(row.get("status") == "timeout" for row in approach_rows)
        ragas: dict[str, Any] = {}
        for metric in metrics:
            values: list[float] = []
            not_evaluable = 0
            metric_errors = 0
            metric_timeouts = 0
            for row in approach_rows:
                if row.get("status") == "timeout":
                    metric_timeouts += 1
                    continue
                if row.get("status") != "ok":
                    metric_errors += 1
                    continue
                result = row.get("metrics", {}).get("ragas", {})
                score = (result.get("scores") or {}).get(metric)
                if score is not None:
                    values.append(float(score))
                elif metric in (result.get("not_evaluable") or {}):
                    not_evaluable += 1
                elif metric in (result.get("metric_errors") or {}) or result.get(
                    "status"
                ) == "error":
                    error_type = str(result.get("error_type") or "")
                    if error_type.endswith("Timeout") or error_type == "TimeoutError":
                        metric_timeouts += 1
                    else:
                        metric_errors += 1
            total = len(approach_rows)
            ragas[metric] = {
                "mean": _mean(values),
                "evaluated": len(values),
                "total": total,
                "not_evaluable": not_evaluable,
                "errors": metric_errors,
                "timeouts": metric_timeouts,
                "coverage": _round(len(values) / total) if total else 0.0,
            }
        judge_scores = list(judge_values.get(approach, []))
        total_questions = len(
            {(row["dataset"]["id"], row["question"]["id"]) for row in approach_rows}
        )
        approach_summaries[approach] = {
            "operational": {
                "attempted": len(approach_rows),
                "successful": len(successful),
                "errors": errors,
                "timeouts": timeouts,
                "mean_latency_ms": _mean(latencies),
                "error_rate": _round((errors + timeouts) / len(approach_rows))
                if approach_rows
                else 0.0,
            },
            "ragas": ragas,
            "judge_panel": {
                "mean": _mean(judge_scores),
                "evaluated": len(judge_scores),
                "total": total_questions,
                "coverage": _round(len(judge_scores) / total_questions)
                if total_questions
                else 0.0,
            },
        }

    ragas_rankings = {
        metric: _ranking(
            {
                approach: approach_summaries[approach]["ragas"][metric]["mean"]
                for approach in approaches
            },
            {
                approach: {
                    "evaluated": approach_summaries[approach]["ragas"][metric]["evaluated"],
                    "total": approach_summaries[approach]["ragas"][metric]["total"],
                }
                for approach in approaches
            },
            higher_is_better=True,
        )
        for metric in metrics
    }
    operational_ranking = _ranking(
        {
            approach: approach_summaries[approach]["operational"]["mean_latency_ms"]
            for approach in approaches
        },
        {
            approach: {
                "evaluated": approach_summaries[approach]["operational"]["successful"],
                "total": approach_summaries[approach]["operational"]["attempted"],
            }
            for approach in approaches
        },
        higher_is_better=False,
    )
    judge_ranking = _ranking(
        {
            approach: approach_summaries[approach]["judge_panel"]["mean"]
            for approach in approaches
        },
        {
            approach: {
                "evaluated": approach_summaries[approach]["judge_panel"]["evaluated"],
                "total": approach_summaries[approach]["judge_panel"]["total"],
            }
            for approach in approaches
        },
        higher_is_better=True,
    )
    total_questions = len(
        {(row["dataset"]["id"], row["question"]["id"]) for row in rows}
    )
    return {
        "coverage": {
            "total_rows": len(rows),
            "ok": sum(row.get("status") == "ok" for row in rows),
            "errors": sum(row.get("status") == "error" for row in rows),
            "timeouts": sum(row.get("status") == "timeout" for row in rows),
        },
        "approaches": approach_summaries,
        "judge_panel": {
            **judge_meta,
            "evaluated_queries": len(judge_evaluated_queries),
            "total_queries": total_questions,
        },
        "rankings": {
            "ragas": ragas_rankings,
            "operational": {"mean_latency_ms": operational_ranking},
            "judge_panel": judge_ranking,
        },
    }


def build_summary(
    rows: list[dict[str, Any]], judgments: dict[str, Any] | None = None
) -> dict[str, Any]:
    if not rows:
        raise ValueError("cannot summarize an empty canonical row set")
    ordered = sorted(
        rows,
        key=lambda row: (
            row["dataset"]["complexity_level"],
            row["dataset"]["id"],
            row["question"]["id"],
            row["approach"]["model"],
        ),
    )
    dataset_ids = sorted({row["dataset"]["id"] for row in ordered})
    judge_scores, judge_queries, judge_meta = _judge_scores(judgments, dataset_ids)
    dataset_summaries: dict[str, Any] = {}
    for dataset_id in sorted(
        dataset_ids,
        key=lambda item: (
            next(row["dataset"]["complexity_level"] for row in ordered
                 if row["dataset"]["id"] == item),
            item,
        ),
    ):
        dataset_rows = [row for row in ordered if row["dataset"]["id"] == dataset_id]
        dataset_summaries[dataset_id] = {
            "label": dataset_rows[0]["dataset"].get("label", dataset_id),
            "complexity_level": dataset_rows[0]["dataset"]["complexity_level"],
            **_scope_summary(
                dataset_rows,
                judge_values=judge_scores.get(dataset_id, {}),
                judge_evaluated_queries=judge_queries.get(dataset_id, set()),
                judge_meta=judge_meta,
            ),
        }

    combined_judges: dict[str, list[float]] = defaultdict(list)
    for dataset_values in judge_scores.values():
        for approach, values in dataset_values.items():
            combined_judges[approach].extend(values)
    overall = _scope_summary(
        ordered,
        judge_values=combined_judges,
        judge_evaluated_queries=set().union(*judge_queries.values()) if judge_queries else set(),
        judge_meta=judge_meta,
    )
    longitudinal: dict[str, list[dict[str, Any]]] = {}
    for approach in sorted({row["approach"]["model"] for row in ordered}):
        points = []
        for dataset_id, dataset_summary in dataset_summaries.items():
            approach_summary = dataset_summary["approaches"].get(approach)
            if approach_summary is None:
                continue
            points.append(
                {
                    "dataset_id": dataset_id,
                    "complexity_level": dataset_summary["complexity_level"],
                    "operational": approach_summary["operational"],
                    "ragas": approach_summary["ragas"],
                    "judge_panel": approach_summary["judge_panel"],
                }
            )
        longitudinal[approach] = points
    return {
        "schema_version": 1,
        "runner_versions": sorted({row.get("runner_version") for row in ordered}),
        "run_ids": sorted({row["run_id"] for row in ordered}),
        "datasets": dataset_summaries,
        "overall": overall,
        "longitudinal": longitudinal,
    }


def write_summary(
    rows_path: Path, output_path: Path, judgments_path: Path | None = None
) -> dict[str, Any]:
    rows = JsonlStore(rows_path).rows()
    judgments = None
    if judgments_path is not None:
        try:
            loaded = json.loads(judgments_path.read_text(encoding="utf-8"))
            if not isinstance(loaded, dict):
                raise TypeError("judgment artifact root must be an object")
            judgments = loaded
        except (OSError, json.JSONDecodeError, TypeError) as exc:
            judgments = {
                "status": "error",
                "error": f"{type(exc).__name__}: {exc}",
                "judges": [],
            }
    summary = build_summary(rows, judgments)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def write_summary_csv(summary: dict[str, Any], output_path: Path) -> None:
    """Write a deterministic long-form projection without mixing metric classes."""
    fields = [
        "scope",
        "dataset_id",
        "complexity_level",
        "approach",
        "metric_class",
        "metric",
        "value",
        "evaluated",
        "total",
        "coverage",
        "errors",
        "timeouts",
        "not_evaluable",
    ]
    scopes = [
        (
            "dataset",
            dataset_id,
            dataset["complexity_level"],
            dataset,
        )
        for dataset_id, dataset in sorted(
            summary.get("datasets", {}).items(),
            key=lambda item: (item[1]["complexity_level"], item[0]),
        )
    ]
    scopes.append(("overall", "", "", summary["overall"]))
    rows: list[dict[str, Any]] = []
    for scope_name, dataset_id, complexity_level, scope in scopes:
        for approach, values in sorted(scope.get("approaches", {}).items()):
            operational = values["operational"]
            attempted = int(operational["attempted"])
            successful = int(operational["successful"])
            base = {
                "scope": scope_name,
                "dataset_id": dataset_id,
                "complexity_level": complexity_level,
                "approach": approach,
            }
            rows.append(
                {
                    **base,
                    "metric_class": "operational",
                    "metric": "mean_latency_ms",
                    "value": operational["mean_latency_ms"],
                    "evaluated": successful,
                    "total": attempted,
                    "coverage": _round(successful / attempted) if attempted else 0.0,
                    "errors": operational["errors"],
                    "timeouts": operational["timeouts"],
                    "not_evaluable": 0,
                }
            )
            for metric, metric_values in sorted(values.get("ragas", {}).items()):
                rows.append(
                    {
                        **base,
                        "metric_class": "ragas",
                        "metric": metric,
                        "value": metric_values["mean"],
                        "evaluated": metric_values["evaluated"],
                        "total": metric_values["total"],
                        "coverage": metric_values["coverage"],
                        "errors": metric_values["errors"],
                        "timeouts": metric_values["timeouts"],
                        "not_evaluable": metric_values["not_evaluable"],
                    }
                )
            judge = values["judge_panel"]
            rows.append(
                {
                    **base,
                    "metric_class": "judge_panel",
                    "metric": "mean_score",
                    "value": judge["mean"],
                    "evaluated": judge["evaluated"],
                    "total": judge["total"],
                    "coverage": judge["coverage"],
                    "errors": 0,
                    "timeouts": 0,
                    "not_evaluable": 0,
                }
            )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
