# 2.3 Hardware Sizing Guide

This repo is hardware-neutral: it can use any Atlas-supported LLM provider source,
including containerized Ollama, host Ollama, GPU-backed Ollama, or remote/cloud
models. The practical hardware requirement depends mostly on whether model
inference is local and how large the selected models are.

## 1. Quick Sizing

| Target | CPU | Memory | Disk | Model backend | Expected fit |
|---|---:|---:|---:|---|---|
| Development and unit tests | 4+ cores | 16 GB | 20 GB free | none required | Code/test work, no live stack |
| Stack smoke with remote/cloud LLMs | 8+ cores | 32 GB | 50 GB free | remote/cloud or small local | Bring up Atlas `gen-ai-rag`, ingest a small corpus, try all seven routes |
| Recommended local canonical-six comparison | 12+ cores | 64 GB+ | 100 GB free | accelerated local inference or remote/cloud | Curated corpus, graph-native corpus, judge runs, repeated matrices |
| Heavy local graph/full-corpus runs | 16+ cores | 96-128 GB+ | 150 GB free | accelerated local inference strongly recommended | Larger corpora, bigger local models, repeated LightRAG rebuilds |

These are practical recommendations, not hard-coded checks. Docker, model
quantization, context length, concurrent requests, and selected corpora can move
the real requirement up or down.

Sizing tiers above describe the six canonical approaches
(`scripts/run-dataset-ladder.py`'s default `--approaches` selection). Passing
`--include-flavor-tier` runs two full matrix/judge passes instead of one: all
seven base approaches (the canonical six plus the experimental `lazy-graph-rag`),
then all twelve flavor tuning aliases (nine flavors of the canonical approaches
plus three `lazy-graph-rag` flavors). The seventh base approach adds its own
on-first-query concept-graph build, which is lighter than LightRAG's
per-document extraction but still additional local inference load — size toward
the heavier tiers above, and expect roughly double the run time, when using
`--include-flavor-tier`.

## 2. What Uses Resources

- **Atlas services:** Supabase/Postgres, Redis, LiteLLM, Open WebUI, backend,
  Weaviate, Neo4j, LightRAG, TEI reranker, and n8n all run together for the
  default showcase path.
- **Vector and graph stores:** Weaviate and Neo4j need enough memory to keep the
  indexed corpus responsive. The committed demo corpora are modest; larger
  enterprise-style corpora need more.
- **Local model inference:** this dominates resource usage when enabled. Model
  disk size is only the first cost; runtime memory also includes KV cache,
  context length, batching, and loaded-model concurrency.
- **LightRAG indexing:** graph extraction is call-heavy. Use a cheaper
  non-reasoning or reliably thinking-disabled model for
  `LIGHTRAG_EXTRACT_LLM_MODEL` and keep extraction concurrency conservative
  unless the model backend has clear headroom.
- **Judging:** the comparison harness can use local judge models. Those are
  additional inference calls after the seven approaches answer.

## 3. Local Model Guidance

The parent-owned `atlas.consumer.yml` imports `config/atlas.env.user`, which
supplies Atlas LightRAG role defaults:

```dotenv
LIGHTRAG_EXTRACT_LLM_MODEL=qwen3.8:latest
LIGHTRAG_KEYWORD_LLM_MODEL=qwen3.8:latest
LIGHTRAG_QUERY_LLM_MODEL=qwen3.8:latest
LIGHTRAG_EXTRACT_LLM_BINDING=openai
LIGHTRAG_EXTRACT_LLM_BINDING_HOST=http://litellm:4000/v1
LIGHTRAG_EXTRACT_MAX_ASYNC_LLM=1
LIGHTRAG_EXTRACT_LLM_TIMEOUT=900
```

Qwen3.8 and `nomic-embed-text` are Atlas catalog defaults, so this consumer no
longer needs `model_sidecars.ollama`. The manifest pins those catalog aliases in
`OLLAMA_USER_MODELS` and explicitly clears `OLLAMA_CUSTOM_MODELS`, which also
replaces stale selections in an existing generated `.env`. If Atlas is using
`LLM_PROVIDER_SOURCE=ollama-localhost`, pull models on the host yourself; Atlas
does not mutate a host-managed Ollama installation.

All Qwen3.8 LightRAG roles traverse LiteLLM, where Atlas applies the catalog's
model-scoped `think:false` request default. This prevents extraction, keyword,
and query calls from paying reasoning-token overhead without applying a global
override to unrelated models. For local runs:

- Prefer a non-reasoning or thinking-disabled model for extraction.
- Prefer accelerated inference for 20B+ local models.
- Avoid CPU-only large-model runs for full six-way canonical matrices unless long
  runtimes are acceptable.
- If memory is tight, reduce model size before increasing timeouts.
- If graph extraction stalls, lower concurrency first; then switch to a smaller
  extraction model.

### 3.1 Model lifecycle status

- Active generation/evaluation default: `qwen3.8:latest`.
- Active embedding default: `nomic-embed-text`; the showcase does not use
  `mxbai-embed-large:latest`, so its planned local retirement does not require a
  repository change.
- `qwen3.6`, `mistral-small3.2`, and `ornith` are not active runtime defaults.
  Their names remain only where historical reports must preserve the provenance
  of already-committed results.
- `gemma4:31b` remains a supported second local judge. The next local panel can
  use `JUDGE_MODELS=qwen3.8:latest,gemma4:31b`.

## 4. Docker Resource Allocation

For Docker Desktop or similar VM-backed runtimes, assign resources to Docker, not
just to the host OS:

- **Minimum live-stack allocation:** 8 CPU cores and 24-32 GB memory.
- **Recommended canonical-six allocation:** 12+ CPU cores and 48-64 GB memory.
- **Leave host headroom:** keep enough memory for the OS and, if used, host-side
  model inference.

On Linux with a native Docker engine, the same sizing applies, but there is no
Docker Desktop VM boundary.

## 5. Corpus Size Expectations

- **Bundled keyword docs only:** useful smoke path, lightest resource use.
- **Curated baseline subset:** good default comparison workload.
- **Graph-native corpus:** better for testing relationship extraction and graph
  query behavior; still moderate.
- **Full corpus / expanded real-world corpora:** treat as a capacity test. Expect
  longer LightRAG indexing and higher vector/graph storage pressure.

## 6. Choosing A Provider Source

Use the provider source that matches your machine and budget:

- `ollama-container-cpu`: easiest local path, but slow for large models.
- `ollama-container-gpu`: best containerized local path when the Docker runtime
  can expose a supported GPU.
- `ollama-localhost`: useful when a host-managed Ollama is already tuned for the
  machine.
- cloud/remote providers: lowest local hardware pressure, but require keys and
  make the run no longer fully local.

The showcase itself does not require one of these paths. It configures Atlas
through public `.env` inputs and lets Atlas/LiteLLM route calls to the selected
backend.
