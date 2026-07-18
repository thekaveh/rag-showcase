#!/usr/bin/env python3
"""Render the canonical static evaluation leaderboards."""
from __future__ import annotations

import argparse
import html
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from compare.leaderboards import build_leaderboards  # noqa: E402


MANIFEST = ROOT / "compare" / "datasets.yaml"
DOCS_MANIFEST = ROOT / "docs" / "manifest.yaml"
DEFAULT_OUTPUT = ROOT / "docs" / "evaluation-results.md"


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    sort_type: Literal["number", "text"] = "number"
    direction: Literal["higher", "lower", "neutral"] = "higher"


TABLE_CAPTIONS = {
    "base-overall": "Overall base-approach leaderboard",
    "base-by-dataset": "Base approaches by measured dataset",
    "flavor-overall": "Overall flavor-alias leaderboard",
    "flavor-by-dataset": "Flavor aliases by measured dataset",
}


def _load_datasets() -> list[dict[str, Any]]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return list(data["datasets"])


def _report_h1() -> str:
    data = yaml.safe_load(DOCS_MANIFEST.read_text(encoding="utf-8"))
    for section in data["sections"]:
        for page in section["pages"]:
            if page["source"] == "evaluation-results.md":
                return f"# {page['number']} {page['title']}"
    return f"# {data['site_name']} Evaluation Results"


def _number(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"


def _integer(value: int | None) -> str:
    return "N/A" if value is None else str(value)


def _coverage(evaluated: int, total: int) -> tuple[float | None, str]:
    if not total:
        return None, "N/A"
    ratio = evaluated / total
    return ratio, f"{evaluated} / {total} ({ratio:.2%})"


def _rate(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.2%}"


def _cell(value: Any, display: str) -> str:
    sort_value = "" if value is None else str(value)
    return (
        f'<td data-sort-value="{html.escape(sort_value)}">'
        f"{html.escape(display)}</td>"
    )


def _cell_value(value: Any, column: Column) -> tuple[Any, str]:
    if isinstance(value, tuple) and len(value) == 2:
        return value
    if column.sort_type == "text":
        return value, "N/A" if value is None else str(value)
    if isinstance(value, int):
        return value, _integer(value)
    return value, _number(value)


def render_table(table_id: str, columns: list[Column], rows: list[dict[str, Any]]) -> str:
    """Render a complete static table with sort/filter metadata only."""
    table_attributes = 'class="results-table" id="{}"'.format(html.escape(table_id))
    if table_id.endswith("by-dataset"):
        table_attributes += ' data-filterable="true"'
    lines = [f"<table {table_attributes}>", f"<caption>{TABLE_CAPTIONS[table_id]}</caption>", "<thead>", "<tr>"]
    for column in columns:
        lines.append(
            '<th scope="col" data-sort-type="{}" data-sort-direction="{}">{}</th>'.format(
                column.sort_type, column.direction, html.escape(column.label)
            )
        )
    lines.extend(["</tr>", "</thead>", "<tbody>"])
    for row in rows:
        attributes = ""
        if table_id.endswith("by-dataset"):
            attributes = (
                ' data-filter-dataset="{}" data-filter-approach="{}" '
                'data-filter-base-family="{}"'.format(
                    html.escape(str(row["dataset"])),
                    html.escape(str(row["approach"])),
                    html.escape(str(row["base-family"])),
                )
            )
        lines.append(f"<tr{attributes}>")
        for column in columns:
            value, display = _cell_value(row.get(column.key), column)
            lines.append(_cell(value, display))
        lines.append("</tr>")
    lines.extend(["</tbody>", "</table>"])
    return "\n".join(lines)


def _judge_columns(models: list[str]) -> list[Column]:
    columns: list[Column] = []
    for model in models:
        columns.extend([
            Column(f"judge:{model}", f"Judge {model}", direction="higher"),
            Column(f"judge-coverage:{model}", f"Judge {model} coverage", direction="higher"),
        ])
    return columns


def _metric_columns(prefix: str, label: str, *, include_rank: bool) -> list[Column]:
    columns: list[Column] = []
    if include_rank:
        columns.append(Column(f"{prefix}-rank", f"{label} rank", direction="lower"))
    columns.extend([
        Column(f"{prefix}-mean", f"{label} mean", direction="higher"),
        Column(f"{prefix}-coverage", f"{label} coverage", direction="higher"),
        Column(f"{prefix}-ineligible", f"{label} ineligible", direction="lower"),
        Column(f"{prefix}-errors", f"{label} errors", direction="lower"),
        Column(f"{prefix}-timeouts", f"{label} timeouts", direction="lower"),
    ])
    return columns


def _operational_columns(*, include_rank: bool) -> list[Column]:
    columns: list[Column] = []
    if include_rank:
        columns.append(Column("latency-rank", "Latency rank", direction="lower"))
    columns.extend([
        Column("latency", "Mean latency (ms)", direction="lower"),
        Column("successful", "Successful", direction="higher"),
        Column("attempted", "Attempted", direction="higher"),
        Column("error-rate", "Error rate", direction="lower"),
        Column("errors", "Errors", direction="lower"),
        Column("timeouts", "Timeouts", direction="lower"),
    ])
    return columns


def _overall_columns(models: list[str], *, flavors: bool) -> list[Column]:
    columns = [
        Column("overall-rank", "Overall judge rank", direction="lower"),
        Column("approach", "Flavor" if flavors else "Approach", sort_type="text", direction="neutral"),
    ]
    if flavors:
        columns.append(Column("base-family", "Base family", sort_type="text", direction="neutral"))
    columns.extend([
        Column("maturity", "Maturity", sort_type="text", direction="neutral"),
        Column("judge-macro", "Dataset-macro judge", direction="higher"),
        Column("judge-weighted", "Query-weighted judge", direction="higher"),
        Column("judge-coverage", "Judge coverage", direction="higher"),
        Column("judge-errors", "Judge errors", direction="lower"),
    ])
    columns.extend(_judge_columns(models))
    columns.extend([
        Column("judge-disagreement", "Judge disagreement", direction="lower"),
        Column("judge-disagreement-coverage", "Judge disagreement comparisons", direction="higher"),
        Column("mean-dataset-rank", "Mean dataset rank", direction="lower"),
        Column("best-dataset-rank", "Best dataset rank", direction="lower"),
        Column("worst-dataset-rank", "Worst dataset rank", direction="lower"),
        Column("query-wins", "Per-query wins", direction="higher"),
    ])
    columns.extend(_metric_columns("answer-relevancy", "Answer relevancy", include_rank=False))
    columns.extend(_metric_columns("faithfulness", "Faithfulness", include_rank=False))
    columns.extend(_operational_columns(include_rank=False))
    return columns


def _by_dataset_columns(models: list[str], *, flavors: bool) -> list[Column]:
    columns = [
        Column("dataset", "Dataset", sort_type="text", direction="neutral"),
        Column("complexity", "Complexity", direction="higher"),
        Column("approach", "Flavor" if flavors else "Approach", sort_type="text", direction="neutral"),
    ]
    if flavors:
        columns.append(Column("base-family", "Base family", sort_type="text", direction="neutral"))
    columns.extend([
        Column("maturity", "Maturity", sort_type="text", direction="neutral"),
        Column("judge-rank", "Judge rank", direction="lower"),
        Column("judge-mean", "Judge mean", direction="higher"),
        Column("judge-coverage", "Judge coverage", direction="higher"),
        Column("judge-errors", "Judge errors", direction="lower"),
    ])
    columns.extend(_judge_columns(models))
    columns.extend([
        Column("judge-disagreement", "Judge disagreement", direction="lower"),
        Column("judge-disagreement-coverage", "Judge disagreement comparisons", direction="higher"),
        Column("query-wins", "Per-query wins", direction="higher"),
    ])
    columns.extend(_metric_columns("answer-relevancy", "Answer relevancy", include_rank=True))
    columns.extend(_metric_columns("faithfulness", "Faithfulness", include_rank=True))
    columns.extend(_operational_columns(include_rank=True))
    return columns


def _metric_values(row: dict[str, Any], prefix: str, metric: dict[str, Any], *, rank: Any = None) -> dict[str, Any]:
    coverage = _coverage(int(metric["evaluated"]), int(metric["total"]))
    values = {
        f"{prefix}-mean": (metric["mean"], _number(metric["mean"], 3)),
        f"{prefix}-coverage": coverage,
        f"{prefix}-ineligible": int(metric["not_evaluable"]),
        f"{prefix}-errors": int(metric["errors"]),
        f"{prefix}-timeouts": int(metric["timeouts"]),
    }
    if rank is not None or f"{prefix}-rank" in row:
        values[f"{prefix}-rank"] = rank
    return values


def _common_values(row: dict[str, Any], models: list[str], *, overall: bool) -> dict[str, Any]:
    judge_coverage = _coverage(int(row["judge_evaluated"]), int(row["judge_total"]))
    values: dict[str, Any] = {
        "approach": row["approach"],
        "base-family": row["base_family"],
        "maturity": row["maturity"],
        "judge-coverage": judge_coverage,
        "judge-errors": int(row["judge_errors"]),
        "judge-disagreement": (row["judge_disagreement"], _number(row["judge_disagreement"], 3)),
        "judge-disagreement-coverage": int(row["judge_disagreement_evaluated"]),
        "query-wins": int(row["query_wins"]),
    }
    for model in models:
        evaluated = int(row["judge_by_model_evaluated"].get(model, 0))
        values[f"judge:{model}"] = (
            row["judge_by_model"].get(model), _number(row["judge_by_model"].get(model), 3)
        )
        values[f"judge-coverage:{model}"] = _coverage(evaluated, int(row["judge_total"]))
    if overall:
        values.update({
            "overall-rank": row["overall_rank"],
            "judge-macro": (row["judge_macro_mean"], _number(row["judge_macro_mean"], 3)),
            "judge-weighted": (row["judge_weighted_mean"], _number(row["judge_weighted_mean"], 3)),
            "mean-dataset-rank": (row["mean_dataset_rank"], _number(row["mean_dataset_rank"], 3)),
            "best-dataset-rank": row["best_dataset_rank"],
            "worst-dataset-rank": row["worst_dataset_rank"],
        })
    else:
        values.update({
            "dataset": row["dataset"],
            "complexity": int(row["complexity"]),
            "judge-rank": row["judge_rank"],
            "judge-mean": (row["judge_mean"], _number(row["judge_mean"], 3)),
        })
    return values


def _overall_rows(rows: list[dict[str, Any]], models: list[str]) -> list[dict[str, Any]]:
    rendered = []
    for row in rows:
        values = _common_values(row, models, overall=True)
        values.update(_metric_values(row, "answer-relevancy", {
            "mean": row["answer_relevancy_mean"], "evaluated": row["answer_relevancy_evaluated"],
            "total": row["answer_relevancy_total"], "not_evaluable": row["answer_relevancy_not_evaluable"],
            "errors": row["answer_relevancy_errors"], "timeouts": row["answer_relevancy_timeouts"],
        }))
        values.update(_metric_values(row, "faithfulness", {
            "mean": row["faithfulness_mean"], "evaluated": row["faithfulness_evaluated"],
            "total": row["faithfulness_total"], "not_evaluable": row["faithfulness_not_evaluable"],
            "errors": row["faithfulness_errors"], "timeouts": row["faithfulness_timeouts"],
        }))
        values.update(_operational_values(row["mean_latency_ms"], row["successful"], row["attempted"], row["error_rate"], row["errors"], row["timeouts"]))
        rendered.append(values)
    return rendered


def _by_dataset_rows(rows: list[dict[str, Any]], models: list[str]) -> list[dict[str, Any]]:
    rendered = []
    for row in rows:
        values = _common_values(row, models, overall=False)
        values.update(_metric_values(row, "answer-relevancy", row["answer_relevancy"], rank=row["answer_relevancy_rank"]))
        values.update(_metric_values(row, "faithfulness", row["faithfulness"], rank=row["faithfulness_rank"]))
        operational = row["operational"]
        values.update(_operational_values(
            operational["mean_latency_ms"], operational["successful"], operational["attempted"],
            operational["error_rate"], operational["errors"], operational["timeouts"], rank=row["latency_rank"],
        ))
        rendered.append(values)
    return rendered


def _operational_values(
    latency: float | None, successful: int, attempted: int, error_rate: float | None,
    errors: int, timeouts: int, *, rank: int | None = None,
) -> dict[str, Any]:
    values = {
        "latency": (latency, _number(latency, 2)),
        "successful": int(successful),
        "attempted": int(attempted),
        "error-rate": (error_rate, _rate(error_rate)),
        "errors": int(errors),
        "timeouts": int(timeouts),
    }
    if rank is not None:
        values["latency-rank"] = rank
    return values


def build_report() -> str:
    """Build the complete canonical Markdown/HTML leaderboard report."""
    leaderboards = build_leaderboards(_load_datasets())
    base = leaderboards["base"]
    flavors = leaderboards["flavors"]
    lines = [
        _report_h1(),
        "",
        "This generated report is the complete static comparison of the committed evaluation",
        "and judgment snapshots. It complements the [evaluation methodology](evaluation-methodology.md),",
        "the [narrative comparison](comparison.md), the [dataset complexity ladder]",
        "(dataset-complexity-report.md), and the [raw result snapshots](results/README.md).",
        "",
        "## 1. Reading the Results",
        "",
        "The default overall order is the **dataset-macro judge mean**: each measured dataset",
        "contributes one equally weighted judge mean. **Query-weighted judge mean** is shown",
        "separately and weights each evaluated query equally. No composite score combines quality,",
        "coverage, latency, or operational reliability.",
        "",
        "Higher judge, answer-relevancy, faithfulness, coverage, successful-response, and",
        "per-query-win values are better. Lower ranks, disagreement, latency, error rate,",
        "errors, and timeouts are better. Coverage is evaluated rows over eligible rows; `N/A`",
        "means no value was recorded and carries an empty machine sort value. Faithfulness",
        "ineligible rows are reported independently: they are not failures and are never coerced",
        "to zero. Ragas evaluator errors and timeouts also remain separate from response errors",
        "and timeouts.",
        "",
        "Base approaches and flavor aliases are intentionally separate tiers. A flavor identifies",
        "its base family but cannot occupy a base-approach rank.",
        "",
        "## 2. Overall Base-Approach Leaderboard",
        "",
        render_table("base-overall", _overall_columns(base["judge_models"], flavors=False), _overall_rows(base["overall"], base["judge_models"])),
        "",
        "## 3. Base Approaches by Dataset",
        "",
        render_table("base-by-dataset", _by_dataset_columns(base["judge_models"], flavors=False), _by_dataset_rows(base["by_dataset"], base["judge_models"])),
        "",
        "## 4. Overall Flavor-Alias Leaderboard",
        "",
        render_table("flavor-overall", _overall_columns(flavors["judge_models"], flavors=True), _overall_rows(flavors["overall"], flavors["judge_models"])),
        "",
        "## 5. Flavor Aliases by Dataset",
        "",
        render_table("flavor-by-dataset", _by_dataset_columns(flavors["judge_models"], flavors=True), _by_dataset_rows(flavors["by_dataset"], flavors["judge_models"])),
        "",
    ]
    return "\n".join(lines)


def _display_path(path: Path) -> Path | str:
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stdout", action="store_true", help="write the report to stdout")
    parser.add_argument("--output", type=Path, help="write the report to this path")
    args = parser.parse_args()
    report = build_report()
    if args.stdout:
        sys.stdout.write(report)
        return
    output = args.output or DEFAULT_OUTPUT
    output.write_text(report, encoding="utf-8")
    print(f"wrote {_display_path(output)}")


if __name__ == "__main__":
    main()
