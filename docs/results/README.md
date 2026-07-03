# Live Run Result Snapshots

This directory holds committed snapshots of live comparison runs. Each run
produces two JSON files per dataset, named
`live-<date>-<dataset>-{matrix,judgments}.json`:

- `*-matrix.json` — the raw per-cell output of [`compare/run_matrix.py`](../../compare/run_matrix.py)
  (every query × every approach/flavor: answer, retrieved sources, server
  metrics, client latency).
- `*-judgments.json` — the local judge-panel scoring of that matrix from
  [`compare/judge.py`](../../compare/judge.py) (per-query mean scores,
  best-answer votes, observed winner).

They are produced by the dataset ladder ([`scripts/run-dataset-ladder.py`](../../scripts/run-dataset-ladder.py))
and consumed by [`compare/report_datasets.py`](../../compare/report_datasets.py),
[`../dataset-complexity-report.md`](../dataset-complexity-report.md), and
[`../comparison.md`](../comparison.md).

## 1. Current snapshots

The live set is whatever [`compare/datasets.yaml`](../../compare/datasets.yaml)
points each measured dataset at — currently the 2026-07-03 run:

- `live-2026-07-03-baseline_curated-{matrix,judgments}.json`
- `live-2026-07-03-graph_native-{matrix,judgments}.json`
- `live-2026-07-03-cyber_threat_intel-{matrix,judgments}.json`

These are the only snapshots the manifest and reports reference. When a dataset
is re-measured, the ladder writes a new dated snapshot and repoints the manifest.

## 2. Historical snapshots

Earlier dated runs are retained as a provenance trail and are **not** referenced
by the manifest or reports — each is superseded by the latest dated run for its
dataset:

- `live-2026-07-01-graph-native-*` and `live-2026-07-01-six-way-*` — the first
  runs, using the earlier hyphenated `graph-native` / combined `six-way` naming
  (before per-dataset snapshots and the underscored `graph_native` id).
- `live-2026-07-02-baseline_curated-*` and `live-2026-07-02-graph_native-*` —
  superseded by the 2026-07-03 re-run.

Keep them for provenance; delete a dated set only when it is genuinely no longer
wanted as history.
