# 5.5 Live Run Result Snapshots

This directory is the committed-artifact ledger for validated, live Atlas-backed
comparison runs. It records evidence and provenance; it does not present ranking
tables. The generated [`evaluation-results.md`](../evaluation-results.md) page is
the canonical complete leaderboard, and the generated
[`dataset-complexity-report.md`](../dataset-complexity-report.md) provides the
dataset ladder and per-query view. The dataset catalog in
[`compare/datasets.yaml`](../../compare/datasets.yaml) identifies the active files
for each measured dataset; older dated files remain provenance only.

## 1. Renewed Four-Artifact Contract

New runs produce four files per dataset with the common prefix
`live-<date>-<dataset>`:

| File | Authority and contents |
|---|---|
| `*-evidence.jsonl` | Canonical, append-safe row per query/approach cell: answer evidence, errors, latency, Ragas state/scores, model metadata, configuration hashes, repository/Atlas revisions, provider/port selection, and generated runtime-registry provenance. |
| `*-evaluation.json` | Deterministic per-dataset/overall aggregates with metric-specific rankings, ties, coverage, failures, unevaluable counts, and optional judge join. |
| `*-matrix.json` | Compatibility view of answers, sources, latency, and approach/flavor metadata; also the judge-panel input. |
| `*-judgments.json` | Optional blinded panel scores, reasons, votes, and observed winners. |

The dataset ladder writes working files under gitignored `compare/results/`,
validates the exact query/alias cross-product, unique row ids, dataset identity,
terminal Ragas disposition for every requested metric, required runtime/config
provenance, exact judge/model/query coverage, and summary coverage, then publishes
the complete set here. It does not publish a partially validated run.

Current runners record both repository HEAD trees and a deterministic SHA-256 of
the complete tracked patch plus every untracked file. The July 17 evaluation was
completed immediately before that stronger capture was added. Its repository
rows therefore use `patch_capture: retrospective-known-scope`: the digest binds a
documented manifest of the known dirty scope, but the exact historical patch
bytes cannot be reconstructed. Atlas was clean in both live phases, so its tree
and empty-patch digest are exact. Future runs use `patch_capture: exact` for both
repositories, including dirty worktrees.

## 2. Current Canonical Snapshots

The active measured set is the 2026-07-17 seven-approach base run plus its
twelve-alias flavor tier:

- `live-2026-07-17-baseline_curated-{matrix,judgments,evidence,evaluation}`
- `live-2026-07-17-graph_native-{matrix,judgments,evidence,evaluation}`
- `live-2026-07-17-cyber_threat_intel-{matrix,judgments,evidence,evaluation}`
- `live-2026-07-17-<dataset>-flavors-{matrix,judgments,evidence,evaluation}`

File extensions follow the contract above: evidence is JSONL and the other three
artifacts are JSON. The base tier contains 42, 56, and 42 successful matrix
cells. The flavor tier contains 72, 96, and 72. All 380 answer cells completed
without response errors or timeouts. The base tier compares the six canonical
approaches and explicitly selected experimental `lazy-graph-rag`; the flavor
tier ranks twelve named variants separately.

Atlas Ragas returned numeric answer relevancy for all successful rows and
coverage-aware faithfulness for rows with exact contexts. LightRAG's answer-only
contract is explicitly ineligible for faithfulness. Operational metrics and the
complete blinded judge panel are fully covered.

## 3. Historical Provenance

The following sets are superseded and are not referenced by active report rows:

- `live-2026-07-01-graph-native-*` and `live-2026-07-01-six-way-*`: first runs,
  before per-dataset underscored ids.
- `live-2026-07-02-baseline_curated-*` and `live-2026-07-02-graph_native-*`:
  superseded by the 2026-07-03 rerun.
- `live-2026-07-03-*`: previous 14-alias flavor ladder retained as provenance;
  it predates the current separated base-family and flavor tiers.
- `live-2026-07-13-*`: previous seven-family base ladder, superseded by the
  2026-07-17 base and flavor rerun with repaired Ragas and rerank integration.

Keep historical sets when their provenance is useful. Deleting them does not alter
the active report unless `compare/datasets.yaml` still references them.

## 4. Consumers

- [`scripts/run-dataset-ladder.py`](../../scripts/run-dataset-ladder.py) produces
  and validates snapshots.
- [`compare/report_datasets.py`](../../compare/report_datasets.py) reads active
  snapshots and generates
  [`dataset-complexity-report.md`](../dataset-complexity-report.md).
- [`compare/judge.py`](../../compare/judge.py) reads the compatibility matrix only.
- [`compare/summarize.py`](../../compare/summarize.py) rebuilds deterministic
  evaluation summaries from canonical JSONL and an optional judgment artifact;
  its optional `--csv-output` is a long-form generated view of the same summary.
- [`evaluation-methodology.md`](../evaluation-methodology.md) defines the full
  ownership, metric, evidence, resume, and ranking contract.
- [`evaluation-results.md`](../evaluation-results.md) renders complete static
  base and flavor leaderboards from the active summaries.
- [`comparison.md`](../comparison.md) interprets those generated rankings.
