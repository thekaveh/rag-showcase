# 5.2 RAG Approaches — Live Comparison

A side-by-side comparison of the RAG approaches in this repo, run against a live
`gen-ai-rag` Atlas stack. The recorded 2026-07-13 run used a local workstation
with host Ollama; that is run metadata, not a repo requirement. See
[`hardware.md`](hardware.md) for hardware guidance without assuming one host shape.

- **Run date:** 2026-07-13
- **Approaches compared:** all 6 canonical approaches plus explicitly selected
  experimental `lazy-graph-rag` (7 total). The earlier 2026-07-03 snapshots
  retain the separate 14-alias flavor ladder as historical tuning evidence.
- **Baseline corpus:** 11-document curated corpus — a MultiHop-RAG subset plus `widget-error-codes.md`.
- **Graph-native corpus:** 10 committed relation-dense dossiers in
  [`corpus/graph_native/`](../corpus/graph_native/).
- **Cyber corpus:** 60 committed MITRE ATT&CK dossiers in
  [`corpus/cyber_threat_intel/`](../corpus/cyber_threat_intel/).
- **Queries:** baseline prompts in [`demo/queries.yaml`](../demo/queries.yaml),
  graph-native prompts in [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml),
  and cyber prompts in [`demo/cyber_threat_intel_queries.yaml`](../demo/cyber_threat_intel_queries.yaml).
- **Harness:** [`compare/run_matrix.py`](../compare/run_matrix.py),
  [`compare/summarize.py`](../compare/summarize.py), and
  [`compare/judge.py`](../compare/judge.py). Renewed runs write canonical evidence
  JSONL, deterministic evaluation JSON, and compatibility matrix/judgment JSON.
  Raw working outputs live under gitignored `compare/results/`; the ladder
  validated and committed matrix, judgments, canonical evidence JSONL, and
  deterministic evaluation JSON for each dataset under [`results/`](results/).
- **Methodology:** the full protocol, model-role map, judge-panel design, and
  dataset-ladder process are documented in
  [`evaluation-methodology.md`](evaluation-methodology.md).

The experimental lazy graph family remains excluded from `default`, but its base
alias was selected explicitly for this run. Its implementation, cold/warm cache
measurements, and keep-experimental decision are documented in
[`lazy-graph-rag.md`](lazy-graph-rag.md).

## 1. Headline

The current base-approach ladder completed all 140 cells on all three measured
datasets without response errors or timeouts. Winners changed as the corpus
became more relational: `n8n-adaptive-rag` and `vanilla-rag` tied at 4.42 on the
baseline corpus, `contextual-rag` led graph-native at 4.12, and experimental
`lazy-graph-rag` led cyber at 3.25. Lazy graph's rank progressed 4/7, 2/7, then
1/7 while averaging 5.12, 6.07, and 11.95 seconds. Default LightRAG was
operational throughout but averaged 67.39, 88.03, and 67.61 seconds and ranked
sixth, equal-sixth, then seventh.

The current run depends on these integration fixes and operating choices:

- scoped `think:false` for local reasoning models via the then-current local
  `backend_plugins/rag/models.yaml` compatibility layer;
- LightRAG role-specific EXTRACT/KEYWORD/QUERY models configured separately;
- LightRAG EXTRACT tuned to `max_async=1` and `timeout=900`;
- `nomic-embed-text` embeddings for graph ingestion;
- LightRAG upload retry on HTTP 409 backpressure, with exact already-processed
  conflicts treated as idempotent during a resumed ingest;
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
MATRIX_DATASET_ID=graph_native \
MATRIX_RUN_ID=manual-graph-native \
MATRIX_RESULTS_FILE=graph_native_matrix.json \
MATRIX_CANONICAL_FILE=graph_native_evidence.jsonl \
MATRIX_SUMMARY_FILE=graph_native_evaluation.json \
uv run python compare/run_matrix.py

JUDGE_MATRIX_FILE=graph_native_matrix.json \
JUDGE_RESULTS_FILE=graph_native_judgments.json \
uv run python compare/judge.py

uv run python compare/summarize.py \
  --rows compare/results/graph_native_evidence.jsonl \
  --output compare/results/graph_native_evaluation.json \
  --csv-output compare/results/graph_native_evaluation.csv \
  --judgments compare/results/graph_native_judgments.json
```

For the dataset-by-dataset view, use the dataset manifest and report generator:

```bash
uv run python compare/report_datasets.py --output docs/dataset-complexity-report.md
```

That report is committed at [`docs/dataset-complexity-report.md`](dataset-complexity-report.md)
and is organized by input dataset complexity rather than by vector/graph collection.

The committed 2026-07-13 ladder used the end-to-end runner so every measured
dataset got a fresh ingest, LightRAG drain, matrix run, judge run, result snapshot,
manifest update, and report regeneration:

```bash
uv run python scripts/run-dataset-ladder.py \
  --date-stamp 2026-07-13 \
  --dataset baseline_curated \
  --dataset graph_native \
  --dataset cyber_threat_intel \
  --approaches vanilla-rag,hybrid-rag,contextual-rag,graph-rag,agentic-rag,n8n-adaptive-rag,lazy-graph-rag
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
   is scoped per model, so it does not leak to unrelated models. The current
   baseline delegates the same model-scoped default to Atlas's model catalog.
2. **Atlas now has a first-class host-Ollama source.** The original run needed an
   ad hoc LiteLLM alias to reach host Ollama. The updated Atlas submodule exposes
   `LLM_PROVIDER_SOURCE=ollama-localhost`, so the repo no longer needs to assume
   any particular host hardware path.
3. **Atlas now exposes LightRAG role-specific model settings.** The current
   submodule maps `LIGHTRAG_EXTRACT_*`, `LIGHTRAG_KEYWORD_*`, and
   `LIGHTRAG_QUERY_*` inputs into LightRAG's native roles. Rag-showcase now sets
   those Atlas inputs instead of patching LightRAG runtime env directly.
4. **LightRAG extraction works, but graph builds remain expensive.** Fresh builds
   drained for all three corpora, including 60 cyber documents producing 66
   chunks. The cyber extraction phase dominated ladder runtime even with the
   dedicated non-reasoning extraction model.
5. **LightRAG query-time rerank is incompatible with the current TEI endpoint wiring.**
   LightRAG sent a Jina-style rerank request to Atlas's TEI reranker and TEI returned
   `422 missing field texts`. Disabling LightRAG query rerank and lowering graph query
   fanout fixed graph-rag answer quality for most queries.
6. **`agentic-rag` is still step-limited.** `MAX_STEPS=4` is too low for several
   synthesis prompts; it does well on single-hop tool use and often stops early on
   multi-step tasks.

## 6. Current Seven-Approach Results

The 2026-07-13 ladder ran three datasets, 20 queries, and seven approaches,
producing 140 successful matrix cells plus complete scores from both judges.
Each dataset has all four canonical artifacts under [`docs/results/`](results/).

| Dataset | Cells | Winner | Judge mean | Mean latency | Current reading |
|---|---:|---|---:|---:|---|
| `baseline_curated` | 42 | `n8n-adaptive-rag` / `vanilla-rag` | 4.42 | 2.23 / 4.28 s | Simple routing and direct vector retrieval remained strongest. |
| `graph_native` | 56 | `contextual-rag` | 4.12 | 11.85 s | Context-prefixed relation dossiers led; lazy graph was second at 3.88 and 6.07 s. |
| `cyber_threat_intel` | 42 | `lazy-graph-rag` | 3.25 | 11.95 s | Deterministic graph expansion won the hardest aggregate and two individual questions. |

All approaches had zero response errors and zero timeouts. Atlas Ragas requests
failed with the tracked evaluator contract defects, so faithfulness and answer
relevancy are explicitly `not evaluated`; those errors do not alter answer,
latency, or blinded-judge coverage. The generated
[`dataset-complexity-report.md`](dataset-complexity-report.md) is the canonical
aggregate and per-query view. The 2026-07-03 14-alias flavor ladder remains
historical evidence for tuning behavior, not the active base-approach ranking.

## 7. Judgment Panel

The scoring pass used `compare/judge.py`, which evaluates stored
matrix answers after all approaches have already run. Its manifest selected local
Ollama models `qwen3.6:latest` and `gemma4:31b`, both called with `temperature=0`
and `think:false`.

The panel was chosen to keep evaluation local and repeatable while avoiding a
single-model judge. For each query, the harness anonymizes and deterministically
shuffles the approach answers, gives the judges the query-specific scoring
rationale from the query YAML, asks for 1-5 scores plus a best-answer letter, and
then aggregates mean score by approach with best-answer votes as the tiebreaker.
The judgment files in `docs/results/` keep the per-judge scores and reasons. The
current harness reads judge models, endpoint, temperature, and optional thinking
from `compare/evaluation.yaml`; environment overrides can use another
OpenAI-compatible provider without changing the runner.

## 8. Graph Findings

The renewed run shows that the graph path is technically healthy: LightRAG indexed
the baseline, graph-native, and cyber corpora, drained extraction, and answered
through the same LiteLLM/Open WebUI route as the other approaches.

The quality story is more nuanced. Default `graph-rag` won three baseline
questions and tied the top mean on the cyber credential-access path, proving the
index and query path can expose useful relationships. It nevertheless ranked
sixth, equal-sixth, and seventh by aggregate while averaging 67-88 seconds. On
four cyber questions it returned `No relevant context found`, so query-time
selection and synthesis remain the immediate weakness. Historical flavor results
still show `graph-rag-fast` can improve some questions and `graph-rag-wide` is too
broad for the current setup.

The cyber corpus is the clearest warning against assuming that a graph-shaped
input automatically favors the LLM-extracted graph endpoint. The ATT&CK docs are
highly relational, but the judges favored experimental lazy graph overall. Lazy
graph also ranked second on graph-native data, made zero index-time LLM calls,
and was much faster than LightRAG. It remains experimental because co-occurrence
edges are untyped and its concept extractor is deliberately lightweight. See
[`lazy-graph-rag.md`](lazy-graph-rag.md) for the measured keep decision.

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
- **Current local judges:** scores are directional, not authoritative. Answers
  are shuffled and anonymized, but the 2026-07-13 panel used two local
  models. The renewed harness keeps that panel separate from Ragas and operational
  metrics.
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
- LightRAG role/query settings are Atlas inputs supplied by the parent-owned
  `config/atlas.env.user` imported by `atlas.consumer.yml`. Use an alternate
  `ATLAS_CONSUMER_MANIFEST` and env-file pair to experiment without editing the
  Atlas submodule.
