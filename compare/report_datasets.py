#!/usr/bin/env python3
"""Build a ranking report by input dataset complexity.

The report intentionally groups by dataset, not by storage collection. A dataset is
the user-facing input package: corpus slice + query set + stored matrix/judgment
snapshots when measured.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from compare.flavors import BASE_APPROACHES  # noqa: E402

MANIFEST = ROOT / "compare" / "datasets.yaml"
DEFAULT_OUTPUT = ROOT / "docs" / "dataset-complexity-report.md"
DOCS_MANIFEST = ROOT / "docs" / "manifest.yaml"


def _load_manifest() -> list[dict]:
    data = yaml.safe_load(MANIFEST.read_text(encoding="utf-8"))
    return sorted(data["datasets"], key=lambda d: d["complexity_level"])


def _report_h1() -> str:
    data = yaml.safe_load(DOCS_MANIFEST.read_text(encoding="utf-8"))
    for section in data["sections"]:
        for page in section["pages"]:
            if page["source"] == "dataset-complexity-report.md":
                return f"# {page['number']} {page['title']}"
    return "# Dataset Complexity Report"


def _mean_scores(judgments: dict) -> dict[str, float]:
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


def _ranking_text(scores: dict[str, float], top_n: int | None = None) -> str:
    if not scores:
        return "pending live run"
    ranked = _ranking(scores)[:top_n]
    return " > ".join(f"{approach} {score:.2f}" for approach, score in ranked)


def _winner(scores: dict[str, float]) -> str:
    ranked = _ranking(scores)
    return ranked[0][0] if ranked else "pending live run"


def _query_rows(judgments: dict) -> list[tuple[str, str, str]]:
    rows = []
    for query in judgments["queries"]:
        scores = {
            approach: float(score)
            for approach, score in query.get("mean_by_approach", {}).items()
        }
        query_id = query.get("query_id") or query.get("id") or query.get("query", "")
        winner = str(query.get("observed_winner") or _winner(scores))
        rows.append((str(query_id), winner, _ranking_text(scores, top_n=3)))
    return rows


def build_report() -> str:
    datasets = _load_manifest()
    # Load each measured judgments snapshot exactly once; every downstream section
    # (rankings, per-query winners, interpretation) derives from these.
    measured_judgments = {
        dataset["id"]: _load_judgments(ROOT / dataset["judgment_snapshot"])
        for dataset in datasets
        if dataset["status"] == "measured"
    }
    measured_scores = {d_id: _mean_scores(j) for d_id, j in measured_judgments.items()}
    measured_rows = {d_id: (_winner(s), _ranking_text(s))
                     for d_id, s in measured_scores.items()}
    lines = [
        _report_h1(),
        "",
        "This report tracks approach rankings by input dataset, ordered from the",
        "simplest curated corpus to increasingly graph-heavy real-world candidates.",
        "It deliberately reports by dataset rather than by vector/graph collection,",
        "because the comparison question is how each RAG approach behaves as the",
        "input problem becomes more relational, temporal, and multi-hop.",
        "Each row also names the Atlas ingestion profile whose revision and job id",
        "are stored with newly generated matrix and judgment snapshots.",
        "",
        "For the run protocol, model roles, approach invocation details, and",
        "judge-panel design, see [`evaluation-methodology.md`](evaluation-methodology.md).",
        "For approach-by-approach internals and tuning surfaces, see",
        "[`approaches.md`](approaches.md).",
        "",
        "## 1. Dataset Complexity Ladder",
        "",
        "| Dataset | Complexity | Status | Atlas ingestion profile | Graph nature | Query file | Source |",
        "|---|---:|---|---|---|---|---|",
    ]
    for dataset in datasets:
        lines.append(
            f"| `{dataset['id']}` | {dataset['complexity_level']} | {dataset['status']} | "
            f"`{dataset.get('ingestion_profile', dataset['id'])}` | "
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
        winner, ranking = measured_rows.get(
            dataset["id"], ("pending live run", "pending live run")
        )
        lines.append(
            f"| `{dataset['id']}` | {dataset['complexity_level']} | {dataset['status']} | "
            f"{winner} | {ranking} |"
        )

    # The interpretation below is DERIVED from the loaded snapshots. This file is
    # regenerated after every ladder run, so baked-in conclusions would silently be
    # republished the first time the data stopped supporting them.
    measured_summaries = []
    for dataset in datasets:
        if dataset["id"] not in measured_rows:
            continue
        prefix = "On" if not measured_summaries else "on"
        measured_summaries.append(
            f"{prefix} `{dataset['id']}`, `{measured_rows[dataset['id']][0]}` leads"
        )
    winner_counts: dict[str, int] = {}
    for judgments in measured_judgments.values():
        for query in judgments["queries"]:
            observed = query.get("observed_winner")
            if observed:
                winner_counts[observed] = winner_counts.get(observed, 0) + 1
    graph_status = ""
    if measured_scores:
        graph_leads = sorted(d_id for d_id, s in measured_scores.items()
                             if _winner(s).startswith("graph-rag"))
        if graph_leads:
            ids = ", ".join(f"`{d}`" for d in graph_leads)
            graph_status = f" `graph-rag` leads on {ids}."
        elif all(any(alias.startswith("graph-rag") for alias in scores)
                 for scores in measured_scores.values()):
            # "across the live rungs" is a per-rung claim: require graph-rag in
            # EVERY measured snapshot, not just one of them.
            graph_status = (" `graph-rag` is measured end to end across the live rungs "
                            "but does not lead any of them.")
        # else: graph-rag absent from at least one snapshot (e.g. an --approaches run
        # that excluded it) — say nothing rather than claim a measurement that didn't
        # happen on every rung.
    flavor_note = ""
    rankings = [_ranking(s) for s in measured_scores.values() if s]
    if rankings and len(rankings) == len(measured_scores):
        last_aliases = {ranking[-1][0] for ranking in rankings}
        if len(last_aliases) == 1:
            worst = next(iter(last_aliases))
            if worst in BASE_APPROACHES:
                # A canonical approach landing last is not a flavor-tuning result —
                # keep the framing honest for flavorless regenerations.
                flavor_note = (f"Across the current snapshots, `{worst}` ranked last "
                               "on every measured dataset.")
            else:
                flavor_note = (f"The live flavor snapshots show one clear tuning result: "
                               f"`{worst}` ranked last on every measured dataset.")
            if worst == "graph-rag-wide":
                # Qualitative context that only applies while the derived fact holds.
                flavor_note += (
                    " Its committed answers are frequently truncated one-token or "
                    "heading-only output — the wide retrieval envelope overflows the "
                    "current LightRAG query setup.")
                fast_wins = winner_counts.get("graph-rag-fast", 0)
                if fast_wins:
                    flavor_note += (
                        f" `graph-rag-fast` was the stronger graph flavor, winning "
                        f"{fast_wins} individual "
                        f"{'query' if fast_wins == 1 else 'queries'} across the measured "
                        "datasets while reducing latency.")

    lines.extend([
        "",
        "## 3. Per-Query Winners",
        "",
        "The **Winner** column is the judge panel's `observed_winner`: the approach with the",
        "highest mean score, breaking ties by best-answer votes. The **Top 3 mean scores**",
        "column ranks by mean only (ties ordered by name), so when several approaches tie on",
        "mean the vote-decided winner can fall outside the listed top three.",
        "",
        "| Dataset | Query | Winner | Top 3 mean scores |",
        "|---|---|---|---|",
    ])
    for dataset in datasets:
        judgments = measured_judgments.get(dataset["id"])
        if not judgments:
            continue
        for query_id, winner, top3 in _query_rows(judgments):
            lines.append(f"| `{dataset['id']}` | `{query_id}` | {winner} | {top3} |")

    rung_sentence = (
        f"The current measured ladder has {len(measured_rows)} "
        f"{'rung' if len(measured_rows) == 1 else 'rungs'}"
        + (". " + "; ".join(measured_summaries) + "." if measured_summaries
           else "; scores appear after the first live ladder run.")
        + graph_status
    )
    lines.extend([
        "",
        "## 4. Interpretation",
        "",
        rung_sentence,
        "",
        "That tells us the next step is not simply adding more documents; it is adding",
        "datasets whose native task requires relational retrieval, temporal event",
        "reasoning, and multi-hop graph paths.",
    ])
    if flavor_note:
        lines.extend(["", flavor_note])
    lines.extend([
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
        # end="": build_report() already ends with a newline; print's default would
        # add a second one, breaking `diff <(… --stdout) <committed report>`.
        print(report, end="")
        return

    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    # The write already succeeded; don't let a nicety crash the CLI. relative_to
    # raises when --output points outside the repo, so fall back to the full path.
    try:
        rel = output.relative_to(ROOT)
    except ValueError:
        rel = output
    print(f"wrote {rel}")


if __name__ == "__main__":
    main()
