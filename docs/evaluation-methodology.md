# 5.1 Evaluation Methodology

This document defines the reproducible evaluation contract for rag-showcase. It
explains ownership, invocation, evidence capture, Atlas-backed Ragas evaluation,
the independent judge panel, resume behavior, and reporting. The generated
dataset view is [`dataset-complexity-report.md`](dataset-complexity-report.md).

## 1. Evaluation Goal and Boundary

The comparison asks:

> Given the same corpus, query set, deployed gateway, and declared model roles,
> how do the six canonical approaches, explicitly selected experimental
> candidates, and their named flavors change as the data becomes more relational
> and graph-shaped?

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
- the six canonical aliases, the explicitly selected experimental lazy-graph
  family, and each approach's evidence capability;
- requested Ragas metrics;
- whether the judge panel is enabled, its OpenAI-compatible endpoint, models,
  temperature, and optional thinking setting;
- retry count, per-cell timeout, evaluator timeout, concurrency, and seed.

Unknown fields and invalid values fail validation before any paid or long-running
call begins. `MATRIX_MODELS` and `MATRIX_FLAVORS` can narrow or expand a run, but
the default remains the six canonical approaches. Secrets are never stored in
the manifest; evaluator and judge credentials are environment inputs.

The checked-in judge configuration routes through the running Atlas LiteLLM
gateway but names no deployment-specific models. Operators must provide model
aliases through `JUDGE_MODELS`; Atlas then decides which backend serves them.
`JUDGE_ENDPOINT`, `JUDGE_API_KEY`, and `JUDGE_THINK=true|false|omit` can instead
target any OpenAI-compatible endpoint, including direct host Ollama when an
experiment explicitly chooses it. Generic endpoints receive only standard
OpenAI-compatible fields by default; LiteLLM cache controls are Atlas-only and
`think` is sent to a generic endpoint only when `JUDGE_THINK` is explicit.

## 3. Deployment and Invocation Flow

All six canonical approaches and the experimental lazy graph route run under
Atlas's `gen-ai-rag` track. Rag-showcase contributes
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
plugin, retrieval, generation, and response-normalization behavior. Matrix requests
set LiteLLM's `no-cache` and `no-store` controls so a renewed run cannot reuse an
answer cached before the selected corpus was ingested. Approach-internal caches,
including LightRAG's query cache, remain part of the measured approach.

The experimental `lazy-graph-rag` base and its fast/balanced/wide flavors require
explicit selection. They do not change the default six-way matrix. The base alias
is represented in the active 2026-07-17 seven-way run; its flavors are measured
in the separate twelve-alias flavor tier.

## 4. Model Roles

The selected Open WebUI model is an approach alias, not necessarily the LLM used
inside that approach.

| Role | Current setup default | Used by | Purpose |
|---|---|---|---|
| `embed` | `nomic-embed-text` | Weaviate-backed approaches, lazy graph, and agent vector tool | Keep dense retrieval embeddings comparable. |
| `light_gen` | `qwen3.6:latest` | vanilla, hybrid, contextual, lazy graph | Shared answer synthesis while retrieval changes. |
| `contextual_blurb` | `qwen3.6:latest` | contextual ingest | Generate context prefixes once at ingest. |
| `agentic` | `qwen3.6:latest` | agentic | ReAct control and tool selection. |
| LightRAG EXTRACT | `mistral-small3.2:24b` | graph ingest | High-volume entity and relationship extraction. |
| LightRAG KEYWORD | `qwen3.6:latest` | graph query | Strict keyword/query decomposition with Atlas-scoped thinking disabled. |
| LightRAG QUERY | `qwen3.6:latest` | graph query | Final graph/vector answer synthesis with Atlas-scoped thinking disabled. |
| n8n classifier | `qwen3.6:latest` | adaptive workflow | Route a request to a downstream approach. |
| Ragas evaluator | `mistral-small3.2:24b` + `nomic-embed-text` | eligible stored evidence | Non-reasoning local faithfulness critic plus semantic answer-relevancy embeddings. |
| Judge panel | Deployment-specific `JUDGE_MODELS`; July 17 used `qwen3.6:latest`, `gemma4:31b` | stored-answer evaluation only | Two-family subjective quality signal without assuming a provider or hardware profile in source control. |

Model names are current configuration, not runner assumptions. Atlas resolves
providers, adapters, capabilities, and model-scoped request defaults. In
particular, Atlas's catalog currently applies `think:false` to its Qwen entry;
rag-showcase no longer injects that property globally.

Mistral Small 3.2 was selected for extraction and Ragas because it is a
non-reasoning instruction model with reliable structured responses, avoiding the
per-call thinking overhead of Qwen during call-heavy work. The evaluator still
returned null on 118 of 300 faithfulness-eligible cells; those rows are retained
as partial coverage rather than retried until a favorable score appears. For the
July 17 run, Qwen and Gemma were selected as two distinct local judge families to
reduce dependence on one subjective critic. They score stored, anonymized answers
only and do not participate in retrieval or generation. The checked-in manifest
intentionally leaves `models: []`; an enabled run must provide deployment-specific
aliases through `JUDGE_MODELS` (or a custom manifest). The default endpoint remains
Atlas LiteLLM, so the runner does not assume Ollama or direct host-service access.

## 5. Approach Processes and Evidence Capabilities

Every approach returns an answer, but not every service exposes the retrieved
contexts needed by context-grounding metrics.

| Approach | Retrieval or routing process | Internal LLM/model calls | Declared evidence capability |
|---|---|---|---|
| `vanilla-rag` | Embed query -> dense search over `RagBase_<profile>` -> stuff top chunks into one prompt. | One `embed` call and one `light_gen` call. | `answer_with_contexts` |
| `hybrid-rag` | Embed query -> Weaviate BM25+dense hybrid search over `RagBase_<profile>` -> TEI rerank -> stuff top chunks. | One `embed` call, one TEI rerank call, one `light_gen` call. | `answer_with_contexts` |
| `contextual-rag` | A showcase post-step derives `RagContextual_<profile>` from Atlas chunks; query-time uses hybrid search + TEI rerank. | Ingest-time `contextual_blurb` calls per chunk; query-time `embed`, TEI rerank, and `light_gen`. | `answer_with_contexts` |
| `graph-rag` | Atlas uploads full documents; LightRAG extracts entities/relationships once and answers through its graph/vector query path. | LightRAG EXTRACT/KEYWORD/QUERY model calls managed by the LightRAG service. | `answer_only` |
| `agentic-rag` | Bounded ReAct loop decides between vector search and LightRAG graph query tools; its trajectory is request-local and is not learned between queries. | Up to the configured agent step limit of `agentic` calls, plus tool calls. | `answer_with_contexts` |
| `n8n-adaptive-rag` | n8n classifies the query, routes to another approach, and preserves the delegated response evidence. | One classifier call, then the selected route's model calls. | `answer_with_contexts` |
| `lazy-graph-rag` (experimental) | Hybrid vector seeds -> deterministic concept/co-occurrence expansion under a relevance budget -> shared generation. | One `embed` and one `light_gen` call; zero index-time LLM calls. | `answer_with_contexts` plus `lazy_graph` index/cache/traversal metadata |

The plugin adds a top-level `rag_showcase` extension to JSON and SSE responses:

```json
{
  "rag_showcase": {
    "schema_version": 1,
    "answer": "unrendered answer text",
    "sources": [{"title": "...", "snippet": "...", "score": 0.82}],
    "metrics": {"seconds": 1.2, "chunks": 5, "llm_calls": 1, "cloud_calls": 0}
  }
}
```

The existing rendered source block and metrics footer remain the compatibility
fallback. Structured evidence wins when both forms are present.

Approach-specific fields are additive. n8n retains delegated `answer`, `sources`,
and metrics, counts the classifier as one additional LLM call, and adds
`adaptive: {route, approach}` rather than mislabeling a route as grounding
context. Lazy graph responses retain the common `schema_version`, `answer`,
`sources`, and `metrics` fields and add `lazy_graph`; the canonical
row stores that object as `evidence.approach_metadata`, and the compatibility matrix
projects it as `approach_metadata`.

LightRAG currently returns an answer and a knowledge-graph source marker, not the
actual text contexts selected during graph/vector synthesis. The runner therefore
does not invent contexts from that marker. Graph answers still receive operational
and judge evaluation. Faithfulness and other context-dependent Ragas metrics are
explicitly `not_evaluable`; answer relevancy remains semantically eligible because
it needs only the question and answer. This distinction is an evidence contract,
not an answer failure or a numeric zero.

## 6. Dataset-Ladder Procedure

The dataset ladder measures one corpus at a time so ingestion provenance and
result files stay dataset-specific. The active 2026-07-17 committed run contains:

| Dataset | Corpus | Queries | Current snapshot generation |
|---|---|---|---|
| `baseline_curated` | `corpus/subset` | `demo/queries.yaml` | Matrix + judgments + canonical evidence/evaluation |
| `graph_native` | `corpus/graph_native` | `demo/graph_native_queries.yaml` | Matrix + judgments + canonical evidence/evaluation |
| `cyber_threat_intel` | `corpus/cyber_threat_intel` | `demo/cyber_threat_intel_queries.yaml` | Matrix + judgments + canonical evidence/evaluation |

For each selected dataset, [`scripts/run-dataset-ladder.py`](../scripts/run-dataset-ladder.py):

1. Validate the dataset's declared `ingestion_profile` and corpus directory.
2. Cold-reset the Atlas stack unless `--no-cold-reset` is set.
3. Start rag-showcase with the profile-scoped base/contextual collection names and
   default ingest skipped.
4. Submit the declared profile to `POST /api/rag/ingestions` and poll its durable
   record until Atlas completes discover, parse, chunk, embed, vector write,
   LightRAG upload, drain, and finalize.
5. Build `RagContextual_<profile>` from the completed Atlas plain chunks. This is
   the only approach-specific ingestion transform retained locally.
6. Run every selected query/alias cell through LiteLLM, appending each completed
   canonical row immediately with the Atlas job id, profile, revision, and digest.
7. Evaluate eligible rows through Atlas and produce the compatibility matrix plus
   first deterministic summary.
8. Validate that every selected matrix cell returned successfully.
9. Run the optional judge panel over stored answers; it carries the same ingestion
   provenance forward.
10. Rebuild the deterministic summary with the judge join.
11. Validate all four artifacts before publishing them to `docs/results/`.
12. Update `compare/datasets.yaml` and regenerate the dataset report.

A cold-reset run deletes only that dataset/date's gitignored working artifacts
before evaluation. Atlas's durable ingestion id, profile revision, and content
digest distinguish the graph/index state from earlier runs. To resume an interrupted
run without rebuilding the graph, rerun one dataset with `--no-cold-reset`; the
existing canonical rows must match that same ingestion provenance.

## 7. Canonical Row Contract and Resume Safety

The canonical artifact is newline-delimited JSON. Each row represents one
`run x dataset x question x alias` cell and records:

- schema, runner, run, and stable row identifiers;
- dataset, question, base approach, flavor, and evidence capability;
- answer, ordered sources/contexts, transport, token usage, and server metrics;
- operational latency and attempt count;
- Ragas status, scores, non-evaluable reasons, and evaluator model metadata;
- pending/disabled judge status;
- seed, configuration hashes, ingestion provenance, repository and Atlas revisions,
  dirty-state flags, project/base-port/provider selection, and hashes plus entry
  inventories for Atlas's generated model and LightRAG query-profile registries;
- durable timeout/error information when the cell fails.

Rows are append-only, flushed, and `fsync`-ed after each cell. Reads and appends use
an OS-appropriate sidecar lock and re-read the complete on-disk artifact while
holding it. Each row id also has a process-level claim held across invocation and
append. Concurrent runners can execute different cells, but a second runner waits
for an in-flight copy of the same cell and then reuses its durable row instead of
calling the model twice. Resume skips an existing stable row. A duplicate row id,
malformed JSONL line, changed query, changed flavor, changed seed, changed config
hash, changed ingestion metadata, or changed runtime provenance aborts resume. The
operator must use a new run
id or remove the stale working artifact; incompatible evidence is never merged
silently.

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
a numeric zero. Every eligible score must be present, numeric, and finite; a
successful HTTP response containing a missing, null, or invalid score produces an
explicit per-metric error. Evaluator timeouts remain separate from other evaluator
errors in aggregate JSON and CSV coverage.

The 2026-07-13 live validation exposed three Atlas evaluator-contract defects:
the pinned Ragas class name had changed, answer relevancy was incorrectly rejected
without contexts, and modern collection metrics were invoked through a retired
synchronous scoring method. Atlas
[#596](https://github.com/thekaveh/atlas/issues/596),
[#597](https://github.com/thekaveh/atlas/issues/597), and
[#659](https://github.com/thekaveh/atlas/issues/659) resolved those defects. At
the current `c744467e` pin, Atlas invokes modern collection metrics through their
async batch API, keeps the client on one event loop, and closes it before loop
teardown. The renewed run therefore records numeric faithfulness and answer
relevancy wherever each metric is eligible; answer-only LightRAG rows remain
explicitly ineligible for faithfulness rather than receiving a fabricated zero.

## 9. Independent Judgment Panel

[`compare/judge.py`](../compare/judge.py) operates only on the compatibility
matrix after approach execution. The current manifest selects the Atlas LiteLLM
endpoint at temperature `0`, with thinking disabled, but deliberately does not
name deployment-specific judge models. Set `JUDGE_MODELS` to two or more aliases
available through that Atlas deployment; the July 17 run used
`qwen3.6:latest,gemma4:31b`. The panel can also be disabled explicitly in a custom
manifest.

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
scores or erase latency/error evidence. A missing, malformed, or non-object judge
artifact marks only the judge section as `error`; operational and Ragas summaries
are still generated.

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
all four to [`docs/results/`](results/) only after validation. The docs generator
copies both JSON and canonical JSONL artifacts to the generated site and wiki, and
the docs check rejects missing local targets. Historical rows
with only matrix/judgment snapshots remain valid and readable.

For spreadsheet analysis, `compare/summarize.py --csv-output <path>` writes a
deterministic long-form view from the same summary. Each row retains its
`operational`, `ragas`, or `judge_panel` metric class plus coverage, errors,
timeouts, and unevaluable counts; the CSV is a generated view, not a fifth source
of truth.

The active 2026-07-17 snapshots implement this contract for all three measured
datasets and both the seven-family and twelve-flavor tiers. Atlas Ragas returns
numeric scores where evidence is eligible. Coverage remains explicit because
LightRAG does not expose contexts for faithfulness and some evaluator calls can
still fail independently without invalidating the answer cell.

## 12. Reproduction and Overrides

Start the stack, then run the default matrix and panel:

```bash
./scripts/start-all.sh
export JUDGE_MODELS=judge-a,judge-b
uv run python compare/run_matrix.py
uv run python compare/judge.py
```

Export the judge aliases before matrix execution so canonical provenance records
the same panel later used by `compare/judge.py`. The runner rejects an enabled
panel with no resolved aliases before issuing approach calls.

`MATRIX_MODELS` selects an exact comma-separated set of model aliases.
`MATRIX_FLAVORS` expands named profiles from `compare/flavors.yaml`. The dataset
runner treats those modes as mutually exclusive to keep result metadata clear.
New snapshots also contain an `ingestion` object. Historical snapshots created
before this migration remain valid but do not retroactively gain Atlas job ids.

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

## 13. Implementation Validation

The 2026-07-17 validation launched the consumer as project `rag-showcase` and
selected host Ollama through Atlas's public provider source; ComfyUI was disabled
because no evaluated approach consumes it. The baseline and graph-native tiers ran
on verified-free block `64500-64609` with Atlas `2229fee9`. The cyber tiers ran on
verified-free block `22000-22109` after the rerank repair, using Atlas `c744467e`.
Every canonical row records its actual split-run base port and Atlas revision. The
repository's final submodule pin is `c744467e`. Hardware is run metadata, not an
assumption in startup or evaluation code.

Each measured dataset received a cold stack reset, fresh Atlas ingestion job,
LightRAG drain, contextual post-processing, base-family matrix, flavor matrix,
Ragas evaluation, and independent Qwen/Gemma judge pass. The published result is:

- 140/140 successful base-family cells;
- 240/240 successful flavor cells;
- zero answer errors and zero answer timeouts;
- complete two-judge coverage for every query;
- numeric answer relevancy for all answer cells and coverage-aware faithfulness
  for approaches that expose exact contexts.

The live flavor run exposed a TEI batch-limit defect in Atlas's LightRAG rerank
adapter when 43 documents exceeded the service's 32-item client limit. Atlas
[#713](https://github.com/thekaveh/atlas/issues/713) and
[#714](https://github.com/thekaveh/atlas/pull/714) added total-budget batching,
global index remapping, and fail-closed behavior. The submodule was advanced to
that merged fix and the invalid pre-fix row was discarded before the complete
rerun. Post-fix requests split into 32- and 11-document TEI batches and all
`graph-rag-rerank` cells completed.

The published panel itself used the direct host-Ollama OpenAI endpoint. That choice
is recorded in every matrix row's planned judge provenance and in each judgment
artifact's resolved runtime. The checked-in default now uses `atlas-litellm`, so a
future run does not require a separately managed host Ollama endpoint.

## 14. Reading the Current Results

The active base ladder shows ranking drift: vanilla retrieval led the baseline,
experimental lazy graph led graph-native dossiers, and contextual retrieval led
the cyber corpus. The flavor tier changed the winners to lazy-graph wide,
hybrid high-recall, and hybrid fast. Default graph-rag was operational but did
not win an aggregate; agentic retrieval remained constrained by bounded planning
and latency.

The canonical rows support direct coverage, failure, latency, answer, context,
Ragas, and judge comparisons. Faithfulness remains intentionally unavailable for
LightRAG answer-only rows; this is an evidence limitation, not an evaluator or
answer failure. See
[`comparison.md`](comparison.md) for narrative findings and
[`approaches.md`](approaches.md) for each approach's internal steps and tuning
surface.
