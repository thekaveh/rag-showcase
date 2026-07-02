# RAG approaches - live comparison

A side-by-side comparison of the RAG approaches in this repo, run against a live
`gen-ai-rag` Atlas stack. The recorded 2026-07-02 run used a Mac Studio M2 Ultra
with 192 GB unified memory and local host Ollama; that is run metadata, not a repo
requirement.

- **Run date:** 2026-07-02
- **Approaches compared:** all 6 - `vanilla-rag`, `hybrid-rag`, `contextual-rag`,
  `graph-rag`, `agentic-rag`, `n8n-adaptive-rag`.
- **Baseline corpus:** 11-document curated subset of MultiHop-RAG plus `widget-error-codes.md`.
- **Graph-native corpus:** 10 committed relation-dense dossiers in
  [`corpus/graph_native/`](../corpus/graph_native/).
- **Queries:** baseline prompts in [`demo/queries.yaml`](../demo/queries.yaml) and
  graph-native prompts in [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml).
- **Harness:** [`compare/run_matrix.py`](../compare/run_matrix.py) and
  [`compare/judge.py`](../compare/judge.py). Raw working outputs are written under
  `compare/results/` and are intentionally gitignored; the committed snapshots for
  this run are [`live-2026-07-02-baseline_curated-matrix.json`](results/live-2026-07-02-baseline_curated-matrix.json)
  / [`live-2026-07-02-baseline_curated-judgments.json`](results/live-2026-07-02-baseline_curated-judgments.json)
  plus [`live-2026-07-02-graph_native-matrix.json`](results/live-2026-07-02-graph_native-matrix.json)
  / [`live-2026-07-02-graph_native-judgments.json`](results/live-2026-07-02-graph_native-judgments.json).

## 0. Headline

The renewed six-way runs completed on both the baseline corpus and a graph-native
corpus built specifically around entities, relationships, shared actors, and causal
chains. `contextual-rag` led the baseline corpus, while `hybrid-rag` led the
graph-native corpus. `graph-rag` is now operational and participated in every cell,
but remains slower and uneven: it answered every graph-shaped query and won some
individual judge votes, yet it is not the aggregate winner on either measured rung.

The key fixes were:

- scoped `think:false` for local reasoning models via `backend_plugins/rag/models.yaml`;
- LightRAG role-specific EXTRACT/KEYWORD/QUERY models configured separately;
- LightRAG EXTRACT tuned to `max_async=1` and `timeout=900`;
- `nomic-embed-text` embeddings for graph ingestion;
- LightRAG upload retry on HTTP 409 backpressure;
- graph query payload tuned to avoid the broken TEI rerank path and reduce context fanout:
  `enable_rerank=false`, `top_k=10`, `chunk_top_k=5`, `max_total_tokens=12000`.

## 1. Reproduce

```bash
./scripts/start-all.sh
uv run python compare/run_matrix.py
uv run python compare/judge.py
```

`MATRIX_MODELS` can restrict the approaches for a partial run:

```bash
MATRIX_MODELS=vanilla-rag,graph-rag uv run python compare/run_matrix.py
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
python3 compare/report_datasets.py --output docs/dataset-complexity-report.md
```

That report is committed at [`docs/dataset-complexity-report.md`](dataset-complexity-report.md)
and is organized by input dataset complexity rather than by vector/graph collection.

## 2. The approaches

See the [README](../README.md#4-the-six-approaches) for the entry table and
[`docs/approaches.md`](approaches.md) for exact internal steps, dependencies,
tuning variables, and measured behavior. In one line each:
`vanilla-rag` is dense top-k; `hybrid-rag` adds BM25 and TEI rerank;
`contextual-rag` retrieves context-prefixed chunks; `graph-rag` delegates to
LightRAG; `agentic-rag` runs a ReAct loop over vector and graph tools; and
`n8n-adaptive-rag` routes through the n8n workflow.

## 3. Environment

| Concern | This run |
|---|---|
| Hardware | Mac Studio M2 Ultra, 192 GB unified memory |
| Generation | host Ollama model alias `qwen3.6-moe` -> `qwen3.6:35b-a3b-coding-mxfp8`, with `think:false` |
| LightRAG extraction/query | host Ollama `mistral-small3.2:24b`, non-reasoning, `num_ctx=8192` |
| Embeddings | `nomic-embed-text`, host Ollama for LightRAG; LiteLLM embedding route for plugin vectors |
| Judges | `qwen3.6:latest` + `gemma4:31b`, local Ollama, `think:false` |

This run uses the current rag-showcase alignment to Atlas's public `LIGHTRAG_*`
role inputs. Current setup configures LightRAG through Atlas and lets Atlas/LiteLLM
decide whether model calls go to container Ollama, host Ollama, GPU container
Ollama, or another configured provider.

## 4. Findings

1. **`think:false` is mandatory for the Qwen reasoning model.** With thinking enabled,
   extraction and generation calls spend time on hidden reasoning. With `think:false`,
   the same local model is roughly 30x faster for this workload. The setting is
   scoped per model in `models.yaml`, so it does not leak to unrelated models.
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

## 5. Results

All 36 cells returned without transport errors.

| Approach | ok cells | avg latency | judge mean |
|---|---:|---:|---:|
| **contextual-rag** | 6/6 | 8.7s | **4.08** |
| n8n-adaptive-rag | 6/6 | 0.5s | 4.00 |
| vanilla-rag | 6/6 | 3.6s | 4.00 |
| hybrid-rag | 6/6 | 6.5s | 3.92 |
| graph-rag | 6/6 | 23.2s | 3.58 |
| agentic-rag | 6/6 | 9.9s | 2.75 |

### 5.1 Per-query winners

| Query | Winner | Notes |
|---|---|---|
| `keyword` | agentic-rag by tiebreak | agentic, graph, hybrid, n8n, and vanilla all scored 5.0 |
| `thematic` | contextual-rag | best synthesis; graph-rag and n8n tied for second at 3.5 |
| `multihop` | agentic-rag | agentic led at 3.5; graph-rag remained weak at 1.0 |
| `factoid` | contextual-rag by tiebreak | graph, vanilla, hybrid, contextual, and n8n all scored 5.0 |
| `context_starved` | agentic-rag by tiebreak | agentic and graph-rag both scored 5.0 |
| `mixed_batch` | hybrid-rag by tiebreak | hybrid, n8n, and vanilla tied at 4.5 |

### 5.2 Interpretation

`contextual-rag` is the best overall default on the baseline corpus: it handled the
thematic prompt well and stayed robust on exact fact questions. `vanilla-rag` and
`n8n-adaptive-rag` are close behind, with n8n benefiting from a fast route decision
and cache hits. `hybrid-rag` remains a predictable production-style retriever, though
it did not beat contextual retrieval on aggregate in this run.

`graph-rag` is no longer excluded. It is included, indexed, and queried successfully.
Its remaining weakness is query-time quality and latency, not indexing availability.
The rerank/query tuning moved it from unusable one-word answers to useful answers on
keyword, thematic, factoid, context-starved, and mixed-batch prompts, but it still
missed the multihop question.

## 6. Graph-native corpus run

To test whether the earlier graph-rag results were partly a corpus mismatch, the
repo now includes a second corpus under [`corpus/graph_native/`](../corpus/graph_native/).
It contains 10 concise real-world dossiers with explicit entity and relationship
statements covering AI partnerships, search antitrust, browser-search economics,
AI competition inquiries, FTX/Alameda, Binance/DOJ, and campaign-finance links.
The query set asks for bridges, shared actors, relationship chains, witnesses,
timelines, and cross-domain regulators.

All 48 cells returned without transport errors.

| Approach | ok cells | avg latency | judge mean |
|---|---:|---:|---:|
| **hybrid-rag** | 8/8 | 9.0s | **4.12** |
| contextual-rag | 8/8 | 11.1s | 4.00 |
| n8n-adaptive-rag | 8/8 | 0.7s | 3.62 |
| vanilla-rag | 8/8 | 3.8s | 3.56 |
| graph-rag | 8/8 | 25.0s | 3.12 |
| agentic-rag | 8/8 | 34.5s | 2.69 |

### 6.1 Per-query winners

| Query | Winner | Notes |
|---|---|---|
| `entity_bridge` | contextual-rag by tiebreak | contextual and graph-rag both scored 4.5 |
| `relationship_chain` | hybrid-rag by tiebreak | hybrid, n8n, and vanilla all scored 5.0 |
| `shared_actor` | contextual-rag | strongest synthesis of common actors across Anthropic/Amazon/Google |
| `timeline_cause` | n8n-adaptive-rag by tiebreak | n8n and vanilla both scored 5.0 |
| `witness_network` | agentic-rag by tiebreak | agentic and graph-rag both scored 4.5 |
| `cloud_model_competition` | contextual-rag by tiebreak | contextual and hybrid both scored 5.0 |
| `default_search_ecosystem` | contextual-rag by tiebreak | contextual and hybrid both scored 5.0 |
| `cross_domain_regulators` | contextual-rag by tiebreak | contextual and hybrid both scored 3.0 |

### 6.2 Interpretation

The graph-native corpus confirms that the graph path is technically healthy: LightRAG
indexed the corpus, drained extraction, and answered all eight graph-shaped prompts.
It does not yet show that this LightRAG configuration is the best answerer for these
prompts. The graph-rag column is still slower than all non-agentic retrievers and
often under-synthesizes compared with hybrid/contextual retrieval over the same
source text, though it tied for first on `entity_bridge` and `witness_network`.

That suggests the remaining work is LightRAG query quality, not only corpus choice:
prompt/mode selection, graph fanout, source-text inclusion, and rerank-provider wiring
are likely more important than simply adding more graph-shaped documents.

## 7. Caveats

- **Small corpus:** the scored run uses the curated 11-doc subset. The full 41-file
  corpus is useful as a stress test, but graph extraction is still expensive locally.
- **Only two rungs measured so far:** the dataset complexity report includes heavier
  real-world graph candidates, but their rankings are marked pending until live matrix
  and judge snapshots are produced.
- **Graph-native corpus is synthetic-curated:** the documents are real-world dossiers
  with source links and explicit relationship bullets, designed to make graph structure
  available. This is a better graph test than the baseline subset, but it is still not
  a large natural enterprise corpus.
- **Local judges:** scores are directional, not authoritative. Answers are shuffled
  and anonymized, but both judges are local models.
- **Cache effects:** n8n and graph-rag include cache hits in some cells.
- **Agentic cap:** `MAX_STEPS=4` materially limits `agentic-rag`.

## 8. Reversibility

- `qwen3.6-moe` was a historical LiteLLM runtime alias used during the early live
  run before the Atlas submodule gained first-class host-Ollama support.
- `models.yaml` keeps `think:false` for the qwen3.6 local models by design.
- LightRAG role/query settings are Atlas `.env` inputs defaulted by rag-showcase
  setup. Override `LIGHTRAG_*` env vars in `infra/.env` to experiment.
