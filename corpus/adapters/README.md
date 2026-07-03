# Real-World Graph Dataset Adapters

This directory documents the external dataset adapters used by the dataset
complexity ladder in [`compare/datasets.yaml`](../../compare/datasets.yaml).
Most heavy datasets are intentionally generated into `corpus/generated/*` rather
than committed directly. The bounded cyber-threat slice is committed under
`corpus/cyber_threat_intel/` because it is the next repeatable graph-native rung.

## 1. STaRK

STaRK is the first target because it is built for retrieval over textual and
relational knowledge bases. It has three useful domains:

- `prime`: precision medicine;
- `mag`: scholarly papers/authors/concepts/citations;
- `amazon`: product graph retrieval.

Suggested setup:

```bash
python3 -m pip install stark-qa
```

Suggested materialization command shape:

```bash
python3 corpus/adapters/stark_export.py --dataset prime --limit 200
python3 corpus/adapters/stark_export.py --dataset mag --limit 200
```

The generated markdown should go under:

- `corpus/generated/stark_prime/`
- `corpus/generated/stark_mag/`

Use the query files:

- [`demo/stark_prime_queries.yaml`](../../demo/stark_prime_queries.yaml)
- [`demo/stark_mag_queries.yaml`](../../demo/stark_mag_queries.yaml)

## 2. OpenAlex Scholarly Graph

OpenAlex is the best real-world scholarly graph source: works, authors,
institutions, concepts, venues, references, and abstracts. Use a bounded topic
slice so LightRAG extraction stays tractable.

Suggested command shape:

```bash
python3 corpus/adapters/openalex_scholarly.py \
  --search "graph rag knowledge graph retrieval" \
  --limit 150 \
  --output corpus/generated/openalex_scholarly
```

Use [`demo/openalex_scholarly_queries.yaml`](../../demo/openalex_scholarly_queries.yaml).

## 3. GDELT Events

GDELT is the best event/timeline graph candidate. Use narrow time windows and
topic filters, then materialize each event cluster as a relation-heavy dossier
with source URLs.

Suggested command shape:

```bash
python3 corpus/adapters/gdelt_events.py \
  --query "artificial intelligence regulation" \
  --start 20240101000000 \
  --end 20240131235959 \
  --limit 150 \
  --output corpus/generated/gdelt_events
```

Use [`demo/gdelt_events_queries.yaml`](../../demo/gdelt_events_queries.yaml).

## 4. Cyber Threat Intelligence

The committed cyber dataset is a bounded MITRE ATT&CK Enterprise export with
retained ATT&CK and STIX IDs:

- ATT&CK intrusion groups, campaigns, malware, tools, techniques, and mitigations;
- explicit `uses` and `mitigates` relation lines with human-readable target names.

Suggested command shape:

```bash
python3 corpus/adapters/cyber_threat_intel.py \
  --limit 60 \
  --output corpus/cyber_threat_intel
```

Use [`demo/cyber_threat_intel_queries.yaml`](../../demo/cyber_threat_intel_queries.yaml).

## 5. Evaluation Loop

For each generated dataset:

```bash
./scripts/start-all.sh
docker exec -e PYTHONPATH=/app/plugins rag-showcase-backend \
  python /app/ingest/ingest.py /app/<corpus_path-from-compare-datasets.yaml>

MATRIX_QUERIES_FILE=demo/<dataset>_queries.yaml \
MATRIX_RESULTS_FILE=<dataset>_matrix.json \
uv run python compare/run_matrix.py

JUDGE_MATRIX_FILE=<dataset>_matrix.json \
JUDGE_RESULTS_FILE=<dataset>_judgments.json \
uv run python compare/judge.py

python3 compare/report_datasets.py --output docs/dataset-complexity-report.md
```

After a successful run, copy the raw result files from `compare/results/` into
`docs/results/`, update `compare/datasets.yaml` from `candidate` to `measured`,
and regenerate the report.
