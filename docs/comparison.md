# RAG approaches - live comparison

A side-by-side comparison of the RAG approaches in this repo, run against a live
`gen-ai-rag` Atlas stack on a single macOS host: Mac Studio M2 Ultra, 192 GB unified
memory. All LLM calls used local Ollama on the host Apple Metal GPU.

- **Run date:** 2026-07-01
- **Approaches compared:** all 6 - `vanilla-rag`, `hybrid-rag`, `contextual-rag`,
  `graph-rag`, `agentic-rag`, `n8n-adaptive-rag`.
- **Corpus:** 11-document curated subset of MultiHop-RAG plus `widget-error-codes.md`.
- **Queries:** the six prompts in [`demo/queries.yaml`](../demo/queries.yaml).
- **Harness:** [`compare/run_matrix.py`](../compare/run_matrix.py) and
  [`compare/judge.py`](../compare/judge.py). Raw run data is written under
  `compare/results/` and is intentionally gitignored.

## 0. Headline

The renewed six-way run completed. `contextual-rag` was the strongest overall result
on this corpus, with `vanilla-rag`, `hybrid-rag`, and `n8n-adaptive-rag` clustered
close behind. `graph-rag` is now operational, but remains slower and uneven: after
the LightRAG fixes it answered 4 of 6 queries usefully, but still failed the
multihop query.

The key fixes were:

- scoped `think:false` for local reasoning models via `backend_plugins/rag/models.yaml`;
- LightRAG role-specific EXTRACT/KEYWORD/QUERY models pointed at host Ollama;
- LightRAG EXTRACT tuned to `max_async=1`, `timeout=900`, and `num_ctx=8192`;
- direct host-Ollama embeddings with `nomic-embed-text` and `EMBEDDING_DIM=768`;
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

## 2. The approaches

See the [README](../README.md#3-the-six-approaches). In one line each:
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

Docker Desktop cannot pass Apple Metal into containers, so Atlas's containerized
Ollama is CPU-only on macOS. The working path is to route big model calls to the
host Ollama at `host.docker.internal:11434`.

## 4. Findings

1. **`think:false` is mandatory for the Qwen reasoning model.** With thinking enabled,
   extraction and generation calls spend time on hidden reasoning. With `think:false`,
   the same local model is roughly 30x faster for this workload. The setting is
   scoped per model in `models.yaml`, so it does not leak to unrelated models.
2. **Atlas needs first-class host-Ollama support on macOS.** Container Ollama works
   functionally but is not viable for large local models on Apple Silicon.
3. **Atlas should expose LightRAG role-specific model settings.** LightRAG supports
   EXTRACT, KEYWORD, QUERY, and VLM roles, but Atlas currently exposes only the
   global `LIGHTRAG_LLM_MODEL` path. Rag-showcase now works around that locally in
   `compose/rag-overlay.yml`.
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
| **contextual-rag** | 6/6 | 9.6s | **4.50** |
| vanilla-rag | 6/6 | 4.7s | 4.17 |
| hybrid-rag | 6/6 | 7.5s | 4.17 |
| n8n-adaptive-rag | 6/6 | 0.6s | 4.17 |
| graph-rag | 6/6 | 23.3s | 3.25 |
| agentic-rag | 6/6 | 5.8s | 2.33 |

### 5.1 Per-query winners

| Query | Winner | Notes |
|---|---|---|
| `keyword` | agentic-rag by tiebreak | all six scored 5.0 |
| `thematic` | contextual-rag | best real synthesis; graph-rag improved but scored 2.0 |
| `multihop` | contextual-rag | graph-rag still returned a weak one-word answer |
| `factoid` | graph-rag by tiebreak | graph, vanilla, hybrid, contextual, and n8n all scored 5.0 |
| `context_starved` | graph-rag by tiebreak | all six scored 4.5 |
| `mixed_batch` | contextual-rag by tiebreak | vanilla/hybrid/contextual/n8n all scored 5.0 |

### 5.2 Interpretation

`contextual-rag` is the best overall default in this run: it handled the thematic and
mixed prompts well and stayed robust on exact fact questions. `hybrid-rag` remains a
good production-style retriever because it is predictable and cheaper than graph-rag.
`vanilla-rag` performed better on this renewed subset than in the earlier failed run
because the widget document was present and retrieved. `n8n-adaptive-rag` mostly
mirrors its selected route and benefits heavily from cache hits.

`graph-rag` is no longer excluded. It is included, indexed, and queried successfully.
Its remaining weakness is query-time quality and latency, not indexing availability.
The rerank/query tuning moved it from unusable one-word answers to useful answers on
keyword, thematic, factoid, context-starved, and mixed-batch prompts, but it still
missed the multihop question.

## 6. Caveats

- **Small corpus:** the scored run uses the curated 11-doc subset. The full 41-file
  corpus is useful as a stress test, but graph extraction is still expensive locally.
- **Local judges:** scores are directional, not authoritative. Answers are shuffled
  and anonymized, but both judges are local models.
- **Cache effects:** n8n and graph-rag include cache hits in some cells.
- **Agentic cap:** `MAX_STEPS=4` materially limits `agentic-rag`.

## 7. Reversibility

- `qwen3.6-moe` is a LiteLLM runtime alias for host Ollama; delete it from LiteLLM if
  you want to return to Atlas defaults.
- `models.yaml` keeps `think:false` for the qwen3.6 local models by design.
- LightRAG role/query settings are rag-showcase overlay defaults, not Atlas changes.
  Override or remove `RAG_LIGHTRAG_*` / `LIGHTRAG_QUERY_*` env vars to experiment.
