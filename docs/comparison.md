# 5.2 RAG Approaches — Live Comparison

A side-by-side comparison of the RAG approaches in this repo, run against a live
`gen-ai-rag` Atlas stack. The recorded 2026-07-03 run used a local workstation
with host Ollama; that is run metadata, not a repo requirement. See
[`hardware.md`](hardware.md) for hardware guidance without assuming one host shape.

- **Run date:** 2026-07-03
- **Approaches compared:** all 6 canonical approaches plus 8 named flavors:
  `vanilla-rag-wide`, `hybrid-rag-high-recall`, `hybrid-rag-fast`,
  `contextual-rag-high-recall`, `graph-rag-fast`, `graph-rag-wide`,
  `agentic-rag-deeper`, and `n8n-adaptive-rag-default`.
- **Baseline corpus:** 11-document curated corpus — a MultiHop-RAG subset plus `widget-error-codes.md`.
- **Graph-native corpus:** 10 committed relation-dense dossiers in
  [`corpus/graph_native/`](../corpus/graph_native/).
- **Cyber corpus:** 60 committed MITRE ATT&CK dossiers in
  [`corpus/cyber_threat_intel/`](../corpus/cyber_threat_intel/).
- **Queries:** baseline prompts in [`demo/queries.yaml`](../demo/queries.yaml),
  graph-native prompts in [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml),
  and cyber prompts in [`demo/cyber_threat_intel_queries.yaml`](../demo/cyber_threat_intel_queries.yaml).
- **Harness:** [`compare/run_matrix.py`](../compare/run_matrix.py) and
  [`compare/judge.py`](../compare/judge.py). Raw working outputs are written under
  `compare/results/` and are intentionally gitignored; the committed snapshots for
  this run are:
  [`baseline matrix`](results/live-2026-07-03-baseline_curated-matrix.json) /
  [`baseline judgments`](results/live-2026-07-03-baseline_curated-judgments.json),
  [`graph-native matrix`](results/live-2026-07-03-graph_native-matrix.json) /
  [`graph-native judgments`](results/live-2026-07-03-graph_native-judgments.json),
  and [`cyber matrix`](results/live-2026-07-03-cyber_threat_intel-matrix.json) /
  [`cyber judgments`](results/live-2026-07-03-cyber_threat_intel-judgments.json).
- **Methodology:** the full protocol, model-role map, judge-panel design, and
  dataset-ladder process are documented in
  [`evaluation-methodology.md`](evaluation-methodology.md).

## 1. Headline

The current ladder completed on all three measured datasets. Winners changed as
the corpus became more relational: `vanilla-rag-wide` led the baseline corpus,
`hybrid-rag-high-recall` led the graph-native dossiers, and
`contextual-rag-high-recall` led the cyber-threat graph slice. `graph-rag` is now
operational and participates in every measured dataset, but tuning matters:
`graph-rag-fast` was useful and won several individual baseline/graph-native
questions, while `graph-rag-wide` frequently returned truncated one-token or
heading-only answers and ranked last on every measured dataset.

At the time of the recorded 2026-07-03 run, the key fixes were:

- scoped `think:false` for local reasoning models via the then-current local
  `backend_plugins/rag/models.yaml` compatibility layer;
- LightRAG role-specific EXTRACT/KEYWORD/QUERY models configured separately;
- LightRAG EXTRACT tuned to `max_async=1` and `timeout=900`;
- `nomic-embed-text` embeddings for graph ingestion;
- LightRAG upload retry on HTTP 409 backpressure;
- TEI rerank batching for high-recall flavors, capped to the reranker's 32-item
  client batch limit;
- graph query payload tuned to avoid the broken TEI rerank path and reduce context fanout:
  `enable_rerank=false`, `top_k=10`, `chunk_top_k=5`, `max_total_tokens=12000`.

## 2. Reproduce

```bash
./scripts/start-all.sh
uv run python compare/run_matrix.py
uv run python compare/judge.py
```

`MATRIX_MODELS` can restrict the approaches for a partial run:

```bash
MATRIX_MODELS=vanilla-rag,graph-rag uv run python compare/run_matrix.py
```

`MATRIX_FLAVORS` expands named profiles from `compare/flavors.yaml`, which is the
benchmark-side companion to the backend `flavors.yaml` used for Open WebUI aliases:

```bash
MATRIX_FLAVORS=default,graph-rag-wide uv run python compare/run_matrix.py
```

The graph-native comparison uses the same harness with alternate input/output files:

```bash
MATRIX_QUERIES_FILE=demo/graph_native_queries.yaml \
MATRIX_RESULTS_FILE=graph_native_matrix.json \
uv run python compare/run_matrix.py

JUDGE_MATRIX_FILE=graph_native_matrix.json \
JUDGE_RESULTS_FILE=graph_native_judgments.json \
uv run python compare/judge.py
```

For the dataset-by-dataset view, use the dataset manifest and report generator:

```bash
uv run python compare/report_datasets.py --output docs/dataset-complexity-report.md
```

That report is committed at [`docs/dataset-complexity-report.md`](dataset-complexity-report.md)
and is organized by input dataset complexity rather than by vector/graph collection.

The committed 2026-07-03 ladder used the end-to-end runner so every measured
dataset got a fresh ingest, LightRAG drain, matrix run, judge run, result snapshot,
manifest update, and report regeneration:

```bash
uv run python scripts/run-dataset-ladder.py \
  --date-stamp 2026-07-03 \
  --dataset baseline_curated \
  --dataset graph_native \
  --dataset cyber_threat_intel \
  --include-candidates \
  --flavors default,vanilla-rag,hybrid-rag,contextual-rag,graph-rag,agentic-rag,n8n-adaptive-rag
```

## 3. The approaches

See the [README](../README.md#4-the-six-approaches) for the entry table and
[`docs/approaches.md`](approaches.md) for exact internal steps, dependencies,
tuning variables, and measured behavior. In one line each:
`vanilla-rag` is dense top-k; `hybrid-rag` adds BM25 and TEI rerank;
`contextual-rag` retrieves context-prefixed chunks; `graph-rag` delegates to
LightRAG; `agentic-rag` runs a ReAct loop over vector and graph tools; and
`n8n-adaptive-rag` routes through the n8n workflow.

## 4. Environment

| Concern | This run |
|---|---|
| Hardware | Mac Studio M2 Ultra, 192 GB unified memory |
| Generation | local Ollama `qwen3.6:latest`, with scoped `think:false` from the then-current local compatibility layer |
| LightRAG extraction/query | host Ollama `mistral-small3.2:24b`, non-reasoning, `num_ctx=8192` |
| Embeddings | `nomic-embed-text`, host Ollama for LightRAG; LiteLLM embedding route for plugin vectors |
| Judges | `qwen3.6:latest` + `gemma4:31b`, local Ollama, `think:false` |

This run uses the current rag-showcase alignment to Atlas's public `LIGHTRAG_*`
role inputs. Current setup configures LightRAG through Atlas and lets Atlas/LiteLLM
decide whether model calls go to container Ollama, host Ollama, GPU container
Ollama, or another configured provider.

## 5. Findings

1. **`think:false` is mandatory for the Qwen reasoning model.** With thinking enabled,
   extraction and generation calls spend time on hidden reasoning. With `think:false`,
   the same local model is roughly 30x faster for this workload. The setting is
   was scoped per model, so it did not leak to unrelated models. The current
   baseline delegates the same model-scoped default to Atlas's model catalog.
2. **Atlas now has a first-class host-Ollama source.** The original run needed an
   ad hoc LiteLLM alias to reach host Ollama. The updated Atlas submodule exposes
   `LLM_PROVIDER_SOURCE=ollama-localhost`, so the repo no longer needs to assume
   any particular host hardware path.
3. **Atlas now exposes LightRAG role-specific model settings.** The current
   submodule maps `LIGHTRAG_EXTRACT_*`, `LIGHTRAG_KEYWORD_*`, and
   `LIGHTRAG_QUERY_*` inputs into LightRAG's native roles. Rag-showcase now sets
   those Atlas inputs instead of patching LightRAG runtime env directly.
4. **LightRAG extraction works with the local overlay, but full-corpus graph builds
   remain expensive.** The 11-doc subset drained cleanly. A 41-file stress ingest
   completed vector/text ingest but LightRAG graph processing did not fully drain
   under the earlier settings and should be treated as a separate capacity test.
5. **LightRAG query-time rerank is incompatible with the current TEI endpoint wiring.**
   LightRAG sent a Jina-style rerank request to Atlas's TEI reranker and TEI returned
   `422 missing field texts`. Disabling LightRAG query rerank and lowering graph query
   fanout fixed graph-rag answer quality for most queries.
6. **`agentic-rag` is still step-limited.** `MAX_STEPS=4` is too low for several
   synthesis prompts; it does well on single-hop tool use and often stops early on
   multi-step tasks.

## 6. Current Flavor Ladder Results

The 2026-07-03 ladder ran three datasets, 20 queries, and 14 aliases, producing
280 matrix cells and judge scores for every dataset. All three dataset runs
completed and wrote committed snapshots under [`docs/results/`](results/).

| Dataset | Matrix cells | Winner | Current reading |
|---|---:|---|---|
| `baseline_curated` | 84 | `vanilla-rag-wide` | Wider dense retrieval was enough on the simplest mixed text corpus. |
| `graph_native` | 112 | `hybrid-rag-high-recall` | Hybrid BM25+dense retrieval with larger rerank pools handled explicit relationship dossiers best on aggregate. |
| `cyber_threat_intel` | 84 | `contextual-rag-high-recall` | Context-prefixed chunks plus high-recall retrieval beat the current graph query settings on the ATT&CK slice. |

The dataset-by-dataset rankings and per-query winners are generated in
[`docs/dataset-complexity-report.md`](dataset-complexity-report.md). That report
is the canonical scored summary for the current run.

## 7. Judgment Panel

The scoring pass used `compare/judge.py`, which evaluates stored matrix answers
after all approaches have already run. The judges were local Ollama models:
`qwen3.6:latest` and `gemma4:31b`, both called with `temperature=0` and
`think:false`.

The panel was chosen to keep evaluation local and repeatable while avoiding a
single-model judge. For each query, the harness anonymizes and deterministically
shuffles the approach answers, gives the judges the query-specific scoring
rationale from the query YAML, asks for 1-5 scores plus a best-answer letter, and
then aggregates mean score by approach with best-answer votes as the tiebreaker.
The judgment files in `docs/results/` keep the per-judge scores and reasons.

## 8. Graph-RAG and Flavor Findings

The renewed run shows that the graph path is technically healthy: LightRAG indexed
the baseline, graph-native, and cyber corpora, drained extraction, and answered
through the same LiteLLM/Open WebUI route as the other approaches.

The quality story is more nuanced. `graph-rag-fast` was the best graph flavor:
it won individual baseline and graph-native questions such as `keyword`,
`factoid`, `entity_bridge`, and sometimes gave stronger answers than default
`graph-rag` with lower latency. `graph-rag-wide`, however, is too broad for the
current LightRAG query setup. It frequently returned truncated strings such as
`The`, `Based`, or `###`, and ranked last on every measured dataset.

The cyber corpus is the clearest warning against assuming that a graph-shaped
input automatically favors the graph endpoint. The ATT&CK docs are highly
relational, but the judges favored `contextual-rag-high-recall` overall. That
points to query-time LightRAG tuning, not only corpus choice, as the next target:
mode selection, fanout, prompt shaping, source-text inclusion, and rerank-provider
wiring are likely more important than adding still more graph-shaped documents.

## 9. Caveats

- **Bounded corpora:** the scored run uses bounded corpora: 11 baseline docs,
  10 graph-native dossiers, and 60 ATT&CK cyber dossiers. Larger graph builds are
  still a separate capacity test.
- **Three rungs measured so far:** the dataset complexity report still includes
  heavier candidates such as STaRK, OpenAlex, and GDELT, but their rankings remain
  pending until live matrix and judge snapshots are produced.
- **Graph-native corpus is synthetic-curated:** the documents are real-world dossiers
  with source links and explicit relationship bullets, designed to make graph structure
  available. This is a better graph test than the baseline subset, but it is still not
  a large natural enterprise corpus.
- **Local judges:** scores are directional, not authoritative. Answers are shuffled
  and anonymized, but both judges are local models.
- **Cache effects:** n8n and graph-rag include cache hits in some cells.
- **Agentic cap:** `MAX_STEPS=4` materially limits `agentic-rag`.
- **Graph-wide caveat:** `graph-rag-wide` is measured but currently a poor tuning;
  it frequently returned truncated answers.

## 10. Reversibility

- `qwen3.6-moe` was a historical LiteLLM runtime alias used during the early live
  run before the Atlas submodule gained first-class host-Ollama support.
- The recorded run used a local `models.yaml` compatibility layer for
  `think:false`; the current baseline removed that layer because Atlas's
  `qwen3.6:latest` catalog entry owns the same scoped request default.
- LightRAG role/query settings are Atlas `.env` inputs defaulted by rag-showcase
  setup. Override `LIGHTRAG_*` env vars in `infra/.env` to experiment.
