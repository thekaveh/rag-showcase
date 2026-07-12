# 5.1 Evaluation Methodology

This document explains how the committed RAG comparison run was organized, which
models were used, how every approach was invoked, and how answer quality was
judged. It is the protocol companion to the generated score report in
[`dataset-complexity-report.md`](dataset-complexity-report.md).

## 1. Evaluation Goal

The comparison asks a narrow question:

> Given the same input corpus, the same query set, and the same OpenAI-compatible
> invocation surface, how do the six rag-showcase approaches and their named
> flavors behave as the input data becomes more relational and graph-shaped?

The run is not a universal benchmark of RAG systems. It is a live, reproducible
showcase test of this repo's six deployed approaches on top of Atlas.

## 2. Evaluated Artifacts

The 2026-07-03 committed run measured three dataset-ladder rungs.

| Dataset | Status | Corpus | Atlas ingestion profile | Queries | Result snapshots |
|---|---|---|---|---|---|
| `baseline_curated` | measured | `corpus/subset` | `baseline_curated` | `demo/queries.yaml` | `docs/results/live-2026-07-03-baseline_curated-*.json` |
| `graph_native` | measured | `corpus/graph_native` | `graph_native` | `demo/graph_native_queries.yaml` | `docs/results/live-2026-07-03-graph_native-*.json` |
| `cyber_threat_intel` | measured | `corpus/cyber_threat_intel` | `cyber_threat_intel` | `demo/cyber_threat_intel_queries.yaml` | `docs/results/live-2026-07-03-cyber_threat_intel-*.json` |

Candidate future rungs are tracked in `compare/datasets.yaml` and surfaced in the
dataset report, but they are not ranked until matrix and judgment snapshots exist.

## 3. Stack and Invocation Surface

All approaches run inside the Atlas `gen-ai-rag` stack vendored at `infra/`.
Rag-showcase contributes a mounted FastAPI plugin under `backend_plugins/rag/`.
Each approach exposes an OpenAI-compatible route:

```text
/rag/<approach>/v1/chat/completions
```

`atlas.consumer.yml` declares those routes and their flavor aliases. Atlas stamps
consumer ownership, validates the routes against the plugin manifest, and merges
the rows into LiteLLM's configuration before startup. Open WebUI and the automated
harness both discover those same aliases through `/v1/models` and call LiteLLM's
`/v1/chat/completions` endpoint, so interactive and measured runs exercise the same
deployment path.

The adaptive workflow follows the same ownership model: its source JSON is checked
in here and declared in `atlas.consumer.yml`; Atlas namespaces and seeds it as
`atlas-consumer-adaptive-rag`. The matrix therefore invokes the same production
webhook that startup probes, rather than a separately imported test workflow.

The six canonical aliases are:

- `vanilla-rag`
- `hybrid-rag`
- `contextual-rag`
- `graph-rag`
- `agentic-rag`
- `n8n-adaptive-rag`

The current flavor run also measured:

- `vanilla-rag-wide`
- `hybrid-rag-high-recall`
- `hybrid-rag-fast`
- `contextual-rag-high-recall`
- `graph-rag-fast`
- `graph-rag-wide`
- `agentic-rag-deeper`
- `n8n-adaptive-rag-default`

## 4. Model Roles

The repo separates approach aliases from underlying model roles. A user selects a
RAG approach such as `contextual-rag`; the approach then calls the configured
embedding, generation, graph, workflow, or judge models internally.

| Role | Default model in this repo | Used by | Why this model/role exists |
|---|---|---|---|
| `embed` | `nomic-embed-text` | `vanilla-rag`, `hybrid-rag`, `contextual-rag`, vector tool inside `agentic-rag` | Small, local embedding model used consistently across Weaviate-backed approaches so their vector retrieval is comparable. |
| `light_gen` | `qwen3.6:latest` | `vanilla-rag`, `hybrid-rag`, `contextual-rag` | Shared answer-generation role for chunk-based approaches, keeping answer synthesis constant while retrieval strategy changes. |
| `contextual_blurb` | `qwen3.6:latest` | `contextual-rag` ingest | Generates short chunk context blurbs once during ingest; same local model family as generation for reproducibility. |
| `agentic` | `qwen3.6:latest` | `agentic-rag` | Tool-using ReAct controller; needs instruction following and tool-call reliability more than raw retrieval speed. |
| LightRAG EXTRACT | `mistral-small3.2:24b` by setup default | `graph-rag`, graph tool inside `agentic-rag` | Non-reasoning, instruction-tuned model for high-volume entity and relationship extraction. Reasoning models were too slow for this call-heavy phase. |
| LightRAG KEYWORD | `mistral-small3.2:24b` by setup default | `graph-rag`, graph tool inside `agentic-rag` | Keeps graph keyword/query decomposition on the same non-reasoning local model as extraction. |
| LightRAG QUERY | `mistral-small3.2:24b` by setup default | `graph-rag`, graph tool inside `agentic-rag` | Produces final LightRAG answers while avoiding chain-of-thought overhead during graph queries. |
| n8n classifier | `qwen3.6:latest` in workflow JSON | `n8n-adaptive-rag` | Classifies a query as `simple` or `complex` before routing to another approach. |
| Judges | `qwen3.6:latest` and `gemma4:31b` | `compare/judge.py` | Two local judge families reduce single-model scoring bias without sending answers to a cloud service. |

The recorded 2026-07-03 run used the then-current local `models.yaml`
compatibility layer to apply `think: false` only to listed Qwen models. The
current baseline has removed that layer: Atlas's model catalog now applies
`request_defaults: {think: false}` to its `qwen3.6:latest` entry, and the
rag-showcase plugin no longer adds model request parameters. Both designs keep
the behavior model-scoped; current replacement models receive the adapter,
capabilities, and request defaults declared by Atlas.

## 5. Approach Processes

Each approach receives the same user query but performs a different retrieval or
routing process.

| Approach | Retrieval or routing process | Internal LLM/model calls | Evidence surfaced |
|---|---|---|---|
| `vanilla-rag` | Embed query -> dense vector search over `RagBase_<profile>` -> stuff top chunks into one prompt. | One `embed` call and one `light_gen` call. | Retrieved plain chunks from Weaviate. |
| `hybrid-rag` | Embed query -> Weaviate BM25+dense hybrid search over `RagBase_<profile>` -> TEI rerank -> stuff top chunks. | One `embed` call, one TEI rerank call, one `light_gen` call. | Reranked plain chunks with scores. |
| `contextual-rag` | A showcase post-step derives `RagContextual_<profile>` from Atlas chunks; query-time uses hybrid search + TEI rerank. | Ingest-time `contextual_blurb` calls per chunk; query-time `embed`, TEI rerank, and `light_gen`. | Reranked contextual chunks. |
| `graph-rag` | Upload full documents to LightRAG; LightRAG extracts entities/relationships and answers through its graph/vector query path. | LightRAG EXTRACT/KEYWORD/QUERY model calls managed by the LightRAG service. | LightRAG knowledge-graph source marker and answer. |
| `agentic-rag` | Bounded ReAct loop decides between vector search and LightRAG graph query tools. | Up to the configured agent step limit of `agentic` model calls, plus tool calls to vector search or LightRAG. | Tool trace. |
| `n8n-adaptive-rag` | n8n classifies query as simple/complex, routes to another approach, and normalizes the response. | One n8n classifier call, then the model calls of the selected downstream route. | Selected route and normalized downstream answer. |

The important contrast is that `hybrid-rag` is not graph RAG. It is hybrid
chunk retrieval: BM25 keyword search plus dense vector search. Only `graph-rag`
and the graph tool inside `agentic-rag` query LightRAG's extracted graph.

## 6. Dataset-Ladder Procedure

The measured ladder was run dataset by dataset so each corpus got a clean ingest
and its own result snapshots.

For each dataset, `scripts/run-dataset-ladder.py` performs this sequence:

1. Validate the dataset's declared `ingestion_profile` and corpus directory.
2. Cold-reset the Atlas stack unless `--no-cold-reset` is set.
3. Start rag-showcase with the profile-scoped base/contextual collection names and
   default ingest skipped.
4. Submit the declared profile to `POST /api/rag/ingestions` and poll its durable
   record until Atlas completes discover, parse, chunk, embed, vector write,
   LightRAG upload, drain, and finalize.
5. Build `RagContextual_<profile>` from the completed Atlas plain chunks. This is
   the only approach-specific ingestion transform retained locally.
6. Run `compare/run_matrix.py` against the dataset's query file, recording ingestion
   id, profile, revision, and content digest in the matrix.
7. Validate that every matrix cell returned successfully.
8. Run `compare/judge.py`; it carries the same ingestion provenance forward.
9. Copy matrix and judgment files into `docs/results/`.
10. Update `compare/datasets.yaml` with snapshot paths and regenerate the report.

The flavor ladder command shape is:

```bash
uv run python scripts/run-dataset-ladder.py \
  --date-stamp 2026-07-03 \
  --dataset baseline_curated \
  --dataset graph_native \
  --dataset cyber_threat_intel \
  --include-candidates \
  --flavors default,vanilla-rag,hybrid-rag,contextual-rag,graph-rag,agentic-rag,n8n-adaptive-rag
```

`MATRIX_MODELS` selects an exact comma-separated set of model aliases.
`MATRIX_FLAVORS` expands named profiles from `compare/flavors.yaml`. The dataset
runner treats those modes as mutually exclusive to keep result metadata clear.
New snapshots also contain an `ingestion` object. Historical snapshots created
before this migration remain valid but do not retroactively gain Atlas job ids.

## 7. Matrix Collection

`compare/run_matrix.py` is the answer collector.

For every query and every selected approach/flavor, it:

1. Posts the query to LiteLLM `/v1/chat/completions`.
2. Uses the selected alias as the OpenAI `model`.
3. Lets LiteLLM route the request to the mounted Atlas backend endpoint.
4. Parses the common answer/source/metrics response wrapper.
5. Records latency, success/error state, base approach, flavor metadata, answer
   text, source text, and metrics.

The resulting matrix JSON is a factual record of what each deployed approach
actually returned before scoring.

## 8. Judgment Panel

`compare/judge.py` scores matrix answers with two local judge models:

- `qwen3.6:latest`
- `gemma4:31b`

Both are called through host Ollama's OpenAI-compatible `/v1/chat/completions`
endpoint. Requests use `temperature: 0` and `think: false`.

The judges were chosen for pragmatic reasons:

- They run locally, so evaluation answers and corpus snippets do not leave the
  machine.
- They represent different model families, reducing dependence on one judge's
  preferences.
- Qwen gives a strong instruction-following local judge, while Gemma provides a
  second, independent scoring signal.
- The pair is fast enough for repeated ladder runs on a local stack.

For every query, the judge harness:

1. Groups all approach answers for that query.
2. Applies a deterministic hash-based shuffle so answer letters are stable but
   not tied to approach order.
3. Hides approach names from the judge prompt.
4. Caps answer text at 1200 characters to keep judge prompts bounded.
5. Supplies the query-specific rationale from the query YAML.
6. Asks each judge to score every answer from 1 to 5 and choose the best answer.
7. Parses strict JSON from the judge response.
8. Aggregates mean score by approach and best-answer vote count.
9. Chooses the observed winner by mean score, with votes as the tiebreaker.

The judge scores are directional, not ground truth. They are useful for comparing
many local runs consistently, but they should be read together with the raw matrix
answers and source traces.

## 9. Report Structure

The documentation is intentionally split by purpose:

| Document | Purpose |
|---|---|
| [`README.md`](../README.md) | Entry point, architecture images, quick start, and top-level result summary. |
| [`approaches.md`](approaches.md) | Detailed internals, dependencies, model roles, tuning surface, and observed behavior for each approach. |
| [`approach-flavor-tuning.md`](approach-flavor-tuning.md) | How named Open WebUI and benchmark aliases map to query-time parameter changes. |
| [`comparison.md`](comparison.md) | Narrative report for the current live run and its operational findings. |
| [`dataset-complexity-report.md`](dataset-complexity-report.md) | Generated ranking table by dataset complexity plus per-query winners. |
| [`results/`](results/) | Committed raw matrix and judgment snapshots for the documented run. |

## 10. Current Reading

The measured results show ranking drift as the input becomes more relational:

- On `baseline_curated`, wider dense retrieval was enough to lead the aggregate.
- On `graph_native`, high-recall hybrid retrieval won the aggregate even though
  `graph-rag-fast` won a relationship-heavy individual question (`entity_bridge`).
- On `cyber_threat_intel`, contextual high-recall retrieval won the aggregate,
  suggesting the current LightRAG query settings still under-synthesize some
  graph-shaped cyber paths.

The graph result should not be read as a failure of graph RAG as a concept. It
shows that the current LightRAG endpoint is operational but still sensitive to
query mode, fanout, reranking compatibility, source-text inclusion, and model-role
choices.
