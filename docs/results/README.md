# 5.4 Live Run Result Snapshots

This directory contains validated, committed snapshots from live Atlas-backed
comparison runs. The dataset catalog in
[`compare/datasets.yaml`](../../compare/datasets.yaml) identifies the active files
for each measured dataset; older dated files remain provenance only.

## 1. Renewed Four-Artifact Contract

New runs produce four files per dataset with the common prefix
`live-<date>-<dataset>`:

| File | Authority and contents |
|---|---|
| `*-evidence.jsonl` | Canonical, append-safe row per query/approach cell: answer evidence, errors, latency, Ragas state/scores, model metadata, and reproducibility hashes. |
| `*-evaluation.json` | Deterministic per-dataset/overall aggregates with metric-specific rankings, ties, coverage, failures, unevaluable counts, and optional judge join. |
| `*-matrix.json` | Compatibility view of answers, sources, latency, and approach/flavor metadata; also the judge-panel input. |
| `*-judgments.json` | Optional blinded panel scores, reasons, votes, and observed winners. |

The dataset ladder writes working files under gitignored `compare/results/`,
validates cell count, unique row ids, dataset identity, summary coverage, and judge
usability, then publishes the complete set here. It does not publish a partially
validated run.

## 2. Current Historical Snapshots

The active measured set is the 2026-07-03 run:

- `live-2026-07-03-baseline_curated-{matrix,judgments}.json`
- `live-2026-07-03-graph_native-{matrix,judgments}.json`
- `live-2026-07-03-cyber_threat_intel-{matrix,judgments}.json`

These files predate the four-artifact contract. Their reported scores come from
the blinded judge panel; no canonical evidence JSONL or Atlas/Ragas summary exists
for that date. The generated dataset report therefore labels canonical evaluation
metrics as `legacy snapshot; rerun required`. Old answers are not retroactively
assigned contexts or grounding scores.

When a dataset is re-measured, the ladder adds `evidence_snapshot` and
`evaluation_snapshot` beside the existing matrix/judgment paths in the dataset
catalog. Reports then prefer the canonical evaluation summary.

## 3. Historical Provenance

The following sets are superseded and are not referenced by active report rows:

- `live-2026-07-01-graph-native-*` and `live-2026-07-01-six-way-*`: first runs,
  before per-dataset underscored ids.
- `live-2026-07-02-baseline_curated-*` and `live-2026-07-02-graph_native-*`:
  superseded by the 2026-07-03 rerun.

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
