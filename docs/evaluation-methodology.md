# 5.1 Evaluation Methodology

This document defines the reproducible evaluation contract for rag-showcase. It
explains ownership, invocation, evidence capture, Atlas-backed Ragas evaluation,
the independent judge panel, resume behavior, and reporting. The generated
dataset view is [`dataset-complexity-report.md`](dataset-complexity-report.md).

## 1. Evaluation Goal and Boundary

The comparison asks:

> Given the same corpus, query set, deployed gateway, and declared model roles,
> how do the six approaches and their named flavors change as the data becomes
> more relational and graph-shaped?

This is a live showcase comparison, not a universal RAG benchmark. The experiment
is consumer-owned:

| Owner | Responsibility |
|---|---|
| Atlas | Start and health-check the generic services; expose LiteLLM model aliases and `POST /api/rag/evaluate`; run configured evaluator and embedding models. |
| rag-showcase | Select datasets, approaches, flavors, metrics, and judges; invoke aliases; normalize evidence; resume runs; aggregate results; publish reports. |

The runner communicates with Atlas only over public HTTP contracts. It does not
import Atlas implementation modules or mutate the `infra/` submodule.

## 2. Versioned Experiment Manifest

[`compare/evaluation.yaml`](../compare/evaluation.yaml) is the evaluation source
of truth. Schema version `1` declares:

- the dataset catalog in [`compare/datasets.yaml`](../compare/datasets.yaml);
- the six canonical aliases and each approach's evidence capability;
- requested Ragas metrics;
- whether the judge panel is enabled, its OpenAI-compatible endpoint, models,
  temperature, and optional thinking setting;
- retry count, per-cell timeout, evaluator timeout, concurrency, and seed.

Unknown fields and invalid values fail validation before any paid or long-running
call begins. `MATRIX_MODELS` and `MATRIX_FLAVORS` can narrow or expand a run, but
the default remains the six canonical approaches. Secrets are never stored in
the manifest; evaluator and judge credentials are environment inputs.

The checked-in judge configuration currently selects a local OpenAI-compatible
endpoint and two local models. That is an experiment default, not a hardware
requirement. `JUDGE_ENDPOINT`, `JUDGE_API_KEY`, `JUDGE_MODELS`, and
`JUDGE_THINK=true|false|omit` can target another compatible provider.

## 3. Deployment and Invocation Flow

All six approaches run under Atlas's `gen-ai-rag` track. Rag-showcase contributes
the mounted FastAPI plugin in [`backend_plugins/rag/`](../backend_plugins/rag/)
and declares routes and aliases in [`atlas.consumer.yml`](../atlas.consumer.yml).

```text
query + alias
    -> Atlas LiteLLM POST /v1/chat/completions
    -> rag-showcase /rag/<approach>/v1/chat/completions
    -> approach-specific retrieval / graph / workflow path
    -> OpenAI-compatible answer + rag_showcase evidence extension
    -> canonical JSONL row
    -> Atlas POST /api/rag/evaluate (eligible Ragas metrics)
    -> deterministic summary + optional blinded judge join
```

Open WebUI and the matrix runner invoke the same LiteLLM aliases. The runner does
not call private approach functions directly, so measurements include gateway,
plugin, retrieval, generation, and response-normalization behavior.

## 4. Model Roles

The selected Open WebUI model is an approach alias, not necessarily the LLM used
inside that approach.

| Role | Current setup default | Used by | Purpose |
|---|---|---|---|
| `embed` | `nomic-embed-text` | Weaviate-backed approaches and agent vector tool | Keep dense retrieval embeddings comparable. |
| `light_gen` | `qwen3.6:latest` | vanilla, hybrid, contextual | Shared answer synthesis while retrieval changes. |
| `contextual_blurb` | `qwen3.6:latest` | contextual ingest | Generate context prefixes once at ingest. |
| `agentic` | `qwen3.6:latest` | agentic | ReAct control and tool selection. |
| LightRAG EXTRACT | `mistral-small3.2:24b` | graph ingest | High-volume entity and relationship extraction. |
| LightRAG KEYWORD | `mistral-small3.2:24b` | graph query | Keyword and query decomposition. |
| LightRAG QUERY | `mistral-small3.2:24b` | graph query | Final graph/vector answer synthesis. |
| n8n classifier | `qwen3.6:latest` | adaptive workflow | Route a request to a downstream approach. |
| Judge panel | `qwen3.6:latest`, `gemma4:31b` | stored-answer evaluation only | Two-family subjective quality signal. |

Model names are current configuration, not runner assumptions. Atlas resolves
providers, adapters, capabilities, and model-scoped request defaults. In
particular, Atlas's catalog currently applies `think:false` to its Qwen entry;
rag-showcase no longer injects that property globally.

## 5. Approach and Evidence Capabilities

Every approach returns an answer, but not every service exposes the retrieved
contexts needed by context-grounding metrics.

| Approach | Core process | Declared evidence capability |
|---|---|---|
| `vanilla-rag` | Dense vector search over `RagBase`, then one generation call. | `answer_with_contexts` |
| `hybrid-rag` | BM25 + dense retrieval, TEI rerank, then generation. | `answer_with_contexts` |
| `contextual-rag` | Hybrid search and rerank over context-prefixed chunks. | `answer_with_contexts` |
| `graph-rag` | LightRAG graph/vector query over an ingest-time knowledge graph. | `answer_only` |
| `agentic-rag` | Bounded ReAct loop over vector and LightRAG tools. | `answer_with_contexts` |
| `n8n-adaptive-rag` | n8n classification, downstream route, normalized response. | `answer_with_contexts` |

The plugin adds a top-level `rag_showcase` extension to JSON and SSE responses:

```json
{
  "rag_showcase": {
    "schema_version": 1,
    "sources": [{"title": "...", "snippet": "...", "score": 0.82}],
    "metrics": {"seconds": 1.2, "chunks": 5, "llm_calls": 1, "cloud_calls": 0}
  }
}
```

The existing rendered source block and metrics footer remain the compatibility
fallback. Structured evidence wins when both forms are present.

LightRAG currently returns an answer and a knowledge-graph source marker, not the
actual text contexts selected during graph/vector synthesis. The runner therefore
does not invent contexts from that marker. Graph answers still receive operational
and judge evaluation, while context-dependent Ragas metrics are explicitly
`not_evaluable`. This is an evidence limitation, not an answer failure or a zero.

## 6. Dataset Ladder

The dataset ladder measures one corpus at a time so ingestion provenance and
result files stay dataset-specific. The 2026-07-03 committed run contains:

| Dataset | Corpus | Queries | Current snapshot generation |
|---|---|---|---|
| `baseline_curated` | `corpus/subset` | `demo/queries.yaml` | Legacy matrix + judgments |
| `graph_native` | `corpus/graph_native` | `demo/graph_native_queries.yaml` | Legacy matrix + judgments |
| `cyber_threat_intel` | `corpus/cyber_threat_intel` | `demo/cyber_threat_intel_queries.yaml` | Legacy matrix + judgments |

For each selected dataset, [`scripts/run-dataset-ladder.py`](../scripts/run-dataset-ladder.py):

1. Optionally cold-resets the stack.
2. Starts Atlas with default ingest skipped.
3. Ingests exactly the selected corpus into Weaviate and LightRAG.
4. Waits until LightRAG extraction drains without failed documents.
5. Runs every selected query/alias cell through LiteLLM.
6. Appends each completed canonical row immediately.
7. Evaluates eligible rows through Atlas.
8. Produces the compatibility matrix and first deterministic summary.
9. Runs the optional judge panel over stored answers.
10. Rebuilds the summary with the judge join.
11. Validates all artifacts before publishing them to `docs/results/`.
12. Updates the dataset catalog and regenerates the dataset report.

## 7. Canonical Row Contract and Resume Safety

The canonical artifact is newline-delimited JSON. Each row represents one
`run x dataset x question x alias` cell and records:

- schema, runner, run, and stable row identifiers;
- dataset, question, base approach, flavor, and evidence capability;
- answer, ordered sources/contexts, transport, token usage, and server metrics;
- operational latency and attempt count;
- Ragas status, scores, non-evaluable reasons, and evaluator model metadata;
- pending/disabled judge status;
- seed, configuration hashes, and ingestion provenance;
- durable timeout/error information when the cell fails.

Rows are append-only, flushed, and `fsync`-ed after each cell. Resume skips an
existing stable row rather than invoking it again. A duplicate row id, malformed
JSONL line, changed query, changed flavor, changed seed, changed config hash, or
changed ingestion metadata aborts resume. The operator must use a new run id or
remove the stale working artifact; incompatible evidence is never merged silently.

## 8. Atlas-Backed Ragas Evaluation

[`compare/run_matrix.py`](../compare/run_matrix.py) sends eligible records to
Atlas `POST /api/rag/evaluate`. The checked-in manifest currently requests:

- `faithfulness`: whether answer claims are supported by retrieved contexts;
- `answer_relevancy`: whether the answer addresses the question.

The client also understands `context_precision` and `context_recall`, which
require a ground-truth/reference value. Metric state is explicit:

| State | Meaning |
|---|---|
| `ok` | All requested metrics were eligible and returned. |
| `partial` | Some metrics returned; others lacked required reference data. |
| `not_evaluable` | Required contexts or ground truth were absent. |
| `error` | Atlas evaluation failed after configured retries. |
| `disabled` | No Ragas metrics or endpoint were selected. |
| `not_run` | The approach cell itself failed before evaluation. |

Evaluator and embedding model names returned by Atlas are stored with scores.
Ragas failures never erase a successful answer, and missing evidence never becomes
a numeric zero.

## 9. Independent Judge Panel

[`compare/judge.py`](../compare/judge.py) operates only on the compatibility
matrix after approach execution. The current manifest selects
`qwen3.6:latest` and `gemma4:31b` at temperature `0`, with thinking disabled for
that local endpoint. The panel is configurable or can be disabled entirely.

For each query, the harness:

1. deterministically shuffles answers with a stable hash;
2. replaces approach names with letters;
3. caps each answer at 1200 characters;
4. supplies the query-specific rationale;
5. requests a 1-5 score for every answer and one best-answer vote;
6. parses strict JSON and normalizes letter case and numeric strings;
7. computes per-approach means and uses votes only as a mean-score tiebreaker.

Judges are a subjective, directional signal. They are kept separate from Ragas
and operational metrics so an unavailable or biased panel cannot change grounding
scores or erase latency/error evidence.

## 10. Metric Taxonomy and Coverage-Aware Ranking

[`compare/evaluation_summary.py`](../compare/evaluation_summary.py) creates
deterministic per-dataset and overall summaries. Rankings never combine unlike
metrics into one opaque score:

- operational: success/error counts and latency;
- Ragas: one ranking per metric;
- judge panel: one separate subjective ranking;
- coverage: evaluated rows/queries versus eligible totals;
- failures and `not_evaluable` counts: visible beside every aggregate.

Ties are emitted as tie groups rather than resolved by input order. Longitudinal
sections show each approach across dataset complexity levels. A high mean with low
coverage must not be read as equivalent to a high mean over every eligible row.

## 11. Result Artifacts

Each renewed dataset run produces four files:

| Suffix | Role |
|---|---|
| `-evidence.jsonl` | Canonical append-safe per-cell evidence and metric rows. |
| `-evaluation.json` | Deterministic coverage-aware aggregate, including judge join when available. |
| `-matrix.json` | Compatibility answer/cell view for readers and judge input. |
| `-judgments.json` | Optional panel verdicts, scores, reasons, and winners. |

Working artifacts live under gitignored `compare/results/`. The ladder publishes
all four to [`docs/results/`](results/) only after validation. Historical rows
with only matrix/judgment snapshots remain valid and readable.

The current 2026-07-03 published snapshots predate the canonical contract. Their
documented rankings are judge-panel rankings; they do not contain Ragas scores.
The generated report labels those datasets `legacy snapshot; rerun required`
instead of fabricating new metrics from old output.

## 12. Reproduction and Overrides

Start the stack, then run the default matrix and panel:

```bash
./scripts/start-all.sh
uv run python compare/run_matrix.py
uv run python compare/judge.py
```

Run an exact subset with explicit durable paths:

```bash
MATRIX_DATASET_ID=graph_native \
MATRIX_QUERIES_FILE=demo/graph_native_queries.yaml \
MATRIX_MODELS=vanilla-rag,graph-rag \
MATRIX_RUN_ID=smoke-graph-native \
MATRIX_CANONICAL_FILE=smoke-graph-native-evidence.jsonl \
MATRIX_SUMMARY_FILE=smoke-graph-native-evaluation.json \
MATRIX_RESULTS_FILE=smoke-graph-native-matrix.json \
uv run python compare/run_matrix.py
```

The same command resumes safely when repeated with unchanged configuration.
Relevant inputs include `MATRIX_MANIFEST_FILE`, `MATRIX_FLAVORS`,
`MATRIX_EVALUATOR_URL`, `MATRIX_EVALUATOR_API_KEY`, `JUDGE_MANIFEST_FILE`,
`JUDGE_MODELS`, `JUDGE_ENDPOINT`, `JUDGE_API_KEY`, and `JUDGE_THINK`.

## 13. Reading the Current Results

The historical ladder shows ranking drift: wider vanilla retrieval led the
baseline corpus, high-recall hybrid retrieval led the graph-native dossiers, and
high-recall contextual retrieval led the cyber corpus. Default graph-rag was
operational but did not win an aggregate; graph flavor behavior varied sharply.

Those conclusions remain useful as a directional historical record, but the next
live ladder is the first run that can support direct faithfulness, answer-relevancy,
coverage, failure, and latency comparisons from canonical evidence. See
[`comparison.md`](comparison.md) for narrative findings and
[`approaches.md`](approaches.md) for each approach's internal steps and tuning
surface.
