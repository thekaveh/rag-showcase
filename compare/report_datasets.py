#!/usr/bin/env python3
"""Build a ranking report by input dataset complexity.

The report intentionally groups by dataset, not by storage collection. A dataset is
the user-facing input package: corpus slice + query set + stored matrix/judgment
snapshots when measured.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "compare" / "datasets.yaml"
DEFAULT_OUTPUT = ROOT / "docs" / "dataset-complexity-report.md"


def _load_manifest() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return sorted(data["datasets"], key=lambda d: d["complexity_level"])


def _mean_scores(judgment_path: Path) -> dict[str, float]:
    judgments = _load_judgments(judgment_path)
    buckets: dict[str, list[float]] = {}
    for query in judgments["queries"]:
        for approach, score in query.get("mean_by_approach", {}).items():
            buckets.setdefault(approach, []).append(float(score))
    return {approach: round(sum(scores) / len(scores), 2)
            for approach, scores in buckets.items() if scores}


def _load_judgments(judgment_path: Path) -> dict:
    return json.loads(judgment_path.read_text(encoding="utf-8"))


def _ranking(scores: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def _ranking_text(scores: dict[str, float]) -> str:
    if not scores:
        return "pending live run"
    return " > ".join(f"{approach} {score:.2f}" for approach, score in _ranking(scores))


def _winner(scores: dict[str, float]) -> str:
    ranked = _ranking(scores)
    return ranked[0][0] if ranked else "pending live run"


def _row(dataset: dict) -> tuple[str, str, str]:
    if dataset["status"] != "measured":
        return "pending live run", "pending live run", "pending live run"
    scores = _mean_scores(ROOT / dataset["judgment_snapshot"])
    return _winner(scores), _ranking_text(scores), f"{len(scores)} approaches scored"


def _top3_text(scores: dict[str, float]) -> str:
    ranked = _ranking(scores)[:3]
    return " > ".join(f"{approach} {score:.2f}" for approach, score in ranked)


def _query_rows(dataset: dict) -> list[tuple[str, str, str]]:
    if dataset["status"] != "measured":
        return []
    judgments = _load_judgments(ROOT / dataset["judgment_snapshot"])
    rows = []
    for query in judgments["queries"]:
        scores = {
            approach: float(score)
            for approach, score in query.get("mean_by_approach", {}).items()
        }
        query_id = query.get("query_id") or query.get("id") or query.get("query", "")
        winner = str(query.get("observed_winner") or _winner(scores))
        rows.append((str(query_id), winner, _top3_text(scores)))
    return rows


def build_report() -> str:
    datasets = _load_manifest()
    measured_rows = {
        dataset["id"]: _row(dataset)
        for dataset in datasets
        if dataset["status"] == "measured"
    }
    lines = [
        "# Dataset Complexity Report",
        "",
        "This report tracks approach rankings by input dataset, ordered from the",
        "simplest curated corpus to increasingly graph-heavy real-world candidates.",
        "It deliberately reports by dataset rather than by vector/graph collection,",
        "because the comparison question is how each RAG approach behaves as the",
        "input problem becomes more relational, temporal, and multi-hop.",
        "",
        "## 1. Dataset Complexity Ladder",
        "",
        "| Dataset | Complexity | Status | Graph nature | Query file | Source |",
        "|---|---:|---|---|---|---|",
    ]
    for dataset in datasets:
        lines.append(
            f"| `{dataset['id']}` | {dataset['complexity_level']} | {dataset['status']} | "
            f"{dataset['graph_nature']} | [`{dataset['queries_file']}`](../{dataset['queries_file']}) | "
            f"{dataset.get('source_url', '')} |"
        )

    lines.extend([
        "",
        "## 2. Ranking Drift by Input Dataset",
        "",
        "| Dataset | Complexity | Status | Winner | Ranking |",
        "|---|---:|---|---|---|",
    ])
    for dataset in datasets:
        winner, ranking, note = measured_rows.get(
            dataset["id"], ("pending live run", "pending live run", "pending live run")
        )
        lines.append(
            f"| `{dataset['id']}` | {dataset['complexity_level']} | {dataset['status']} | "
            f"{winner} | {ranking} |"
        )

    measured_summaries = []
    for dataset in datasets:
        if dataset["id"] not in measured_rows:
            continue
        prefix = "On" if not measured_summaries else "on"
        measured_summaries.append(
            f"{prefix} `{dataset['id']}`, `{measured_rows[dataset['id']][0]}` leads"
        )
    graph_status = ""
    if measured_rows:
        graph_status = (
            " `graph-rag` is now measured end to end across the live rungs, but it is "
            "not yet the aggregate winner; its strongest individual scores appear on "
            "relationship-heavy questions."
        )

    lines.extend([
        "",
        "## 3. Per-Query Winners",
        "",
        "| Dataset | Query | Winner | Top 3 mean scores |",
        "|---|---|---|---|",
    ])
    for dataset in datasets:
        for query_id, winner, top3 in _query_rows(dataset):
            lines.append(f"| `{dataset['id']}` | `{query_id}` | {winner} | {top3} |")

    lines.extend([
        "",
        "## 4. Interpretation",
        "",
        f"The current measured ladder has {len(measured_rows)} "
        f"{'rung' if len(measured_rows) == 1 else 'rungs'}. "
        + "; ".join(measured_summaries)
        + "."
        + graph_status,
        "",
        "That tells us the next step is not simply adding more documents; it is adding",
        "datasets whose native task requires relational retrieval, temporal event",
        "reasoning, and multi-hop graph paths.",
        "",
        "The live flavor run also surfaced one clear tuning result: `graph-rag-wide`",
        "is too broad for the current LightRAG query setup. It frequently returned",
        "truncated one-token or heading-only answers and ranked last on every",
        "measured dataset. `graph-rag-fast` was the stronger graph flavor, winning",
        "several baseline and graph-native questions while reducing latency.",
        "",
        "The candidate rungs are intentionally heavier: STaRK-Prime and STaRK-MAG",
        "are semi-structured retrieval benchmarks; OpenAlex adds a real scholarly",
        "citation/author/institution graph; GDELT adds event-time actor/location",
        "graphs; and the measured cyber slice adds threat-technique, software,",
        "campaign, intrusion-group, and mitigation relationships. Scores for",
        "candidate rungs should be added only after live",
        "matrix and judge runs produce committed snapshots.",
        "",
        "## 5. Candidate Dataset Sources",
        "",
        "- STaRK: semi-structured textual + relational retrieval benchmark with Amazon, MAG, and Prime domains.",
        "- OpenAlex: CC0 scholarly graph of works, authors, institutions, concepts, venues, and citations.",
        "- GDELT: global event/news graph with actors, events, locations, themes, sources, and timelines.",
        "- MITRE ATT&CK: measured bounded cyber graph over intrusion groups, campaigns, software, techniques, and mitigations.",
        "",
    ])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdout", action="store_true", help="print report instead of writing")
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT), help="markdown output path")
    args = parser.parse_args()

    report = build_report()
    if args.stdout:
        print(report)
        return

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    print(f"wrote {output.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
