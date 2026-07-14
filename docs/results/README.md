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

## 2. Current Canonical Snapshots

The active measured set is the 2026-07-13 seven-approach run:

- `live-2026-07-13-baseline_curated-{matrix,judgments,evidence,evaluation}`
- `live-2026-07-13-graph_native-{matrix,judgments,evidence,evaluation}`
- `live-2026-07-13-cyber_threat_intel-{matrix,judgments,evidence,evaluation}`

File extensions follow the contract above: evidence is JSONL and the other three
artifacts are JSON. The run contains 42, 56, and 42 successful matrix cells,
respectively, with no response errors or timeouts. It compares the six canonical
base approaches and explicitly selected experimental `lazy-graph-rag`.

The Atlas Ragas endpoint rejected the requested evaluations because of tracked
evaluator contract issues Atlas #596 and #597. Each evidence row records that
error; summaries therefore report zero Ragas coverage instead of inventing
scores. Operational metrics and the complete blinded judge panel are independently
valid and fully covered.

## 3. Historical Provenance

The following sets are superseded and are not referenced by active report rows:

- `live-2026-07-01-graph-native-*` and `live-2026-07-01-six-way-*`: first runs,
  before per-dataset underscored ids.
- `live-2026-07-02-baseline_curated-*` and `live-2026-07-02-graph_native-*`:
  superseded by the 2026-07-03 rerun.
- `live-2026-07-03-*`: previous 14-alias flavor ladder, retained as provenance
  and superseded as the active base-approach comparison by 2026-07-13.

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
