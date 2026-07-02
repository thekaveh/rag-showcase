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
    judgments = json.loads(judgment_path.read_text(encoding="utf-8"))
    buckets: dict[str, list[float]] = {}
    for query in judgments["queries"]:
        for approach, score in query.get("mean_by_approach", {}).items():
            buckets.setdefault(approach, []).append(float(score))
    return {approach: round(sum(scores) / len(scores), 2)
            for approach, scores in buckets.items() if scores}


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


def build_report() -> str:
    datasets = _load_manifest()
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
        winner, ranking, note = _row(dataset)
        lines.append(
            f"| `{dataset['id']}` | {dataset['complexity_level']} | {dataset['status']} | "
            f"{winner} | {ranking} |"
        )

    lines.extend([
        "",
        "## 3. Interpretation",
        "",
        "The current measured ladder has two rungs. On the baseline curated corpus,",
        "`contextual-rag` leads, with vanilla, hybrid, and n8n close behind. On the",
        "graph-native dossiers, `contextual-rag` still leads and `graph-rag` is",
        "measured but not yet dominant. That tells us the next step is not simply",
        "adding more documents; it is adding datasets whose native task requires",
        "relational retrieval, temporal event reasoning, and multi-hop graph paths.",
        "",
        "The candidate rungs are intentionally heavier: STaRK-Prime and STaRK-MAG",
        "are semi-structured retrieval benchmarks; OpenAlex adds a real scholarly",
        "citation/author/institution graph; GDELT adds event-time actor/location",
        "graphs; and the cyber slice adds threat-technique-vulnerability-product",
        "relationships. Scores for those rungs should be added only after live",
        "matrix and judge runs produce committed snapshots.",
        "",
        "## 4. Candidate Dataset Sources",
        "",
        "- STaRK: semi-structured textual + relational retrieval benchmark with Amazon, MAG, and Prime domains.",
        "- OpenAlex: CC0 scholarly graph of works, authors, institutions, concepts, venues, and citations.",
        "- GDELT: global event/news graph with actors, events, locations, themes, sources, and timelines.",
        "- MITRE ATT&CK + NVD: public cyber graph over groups, software, techniques, mitigations, CVEs, CWEs, and CPE products.",
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
