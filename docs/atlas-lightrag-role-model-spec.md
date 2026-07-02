# Atlas LightRAG Role Model Integration Spec

Date: 2026-07-01

Status: implemented upstream in Atlas and retained here as a historical handoff
record. Rag-showcase now configures these Atlas inputs through `infra/.env`
instead of patching LightRAG's runtime environment directly.

## Purpose

Atlas should expose LightRAG v1.5 role-specific LLM configuration so graph indexing can use a fast, non-reasoning extraction model while query answering can use a stronger model. This avoids routing LightRAG's high-volume extraction calls through a slow reasoning model and gives downstream projects a supported way to tune graph RAG without patching Atlas internals.

## Problem

Before the Atlas fix, Atlas modeled LightRAG with one chat model:

- `LIGHTRAG_LLM_MODEL` is resolved during init.
- Init writes `/app/data/.env` with `LLM_MODEL`, `EMBEDDING_MODEL`, and `EMBEDDING_DIM`.
- The runtime container sources that file before starting `python -m lightrag.api.lightrag_server`.

LightRAG v1.5.4 supports separate roles:

- `EXTRACT`: entity and relationship extraction plus merge summaries.
- `KEYWORD`: keyword extraction.
- `QUERY`: answer generation.
- `VLM`: vision-language work.

The native LightRAG server reads role-specific environment variables such as `EXTRACT_LLM_MODEL`, `KEYWORD_LLM_MODEL`, and `QUERY_LLM_MODEL`, then falls back to `LLM_MODEL` when a role is not set. Atlas now exposes and maps those role variables.

That is the wrong shape for local graph RAG. Entity and relationship extraction makes many calls per document and needs strict structured output, not long reasoning traces. A reasoning model such as Qwen 3.6 MoE can be acceptable for user-facing answers with `think:false`, but it is a poor default for extraction because any missed thinking override or long context startup turns indexing into timeouts.

## Desired Behavior

Atlas should make role-specific LightRAG model selection first-class while preserving the existing single-model behavior as the default fallback.

Minimum supported configuration:

```dotenv
LIGHTRAG_LLM_MODEL=qwen3.6:latest
LIGHTRAG_EXTRACT_LLM_MODEL=mistral-small3.2:24b
LIGHTRAG_KEYWORD_LLM_MODEL=mistral-small3.2:24b
LIGHTRAG_QUERY_LLM_MODEL=qwen3.6:latest
```

Expected runtime mapping:

```dotenv
LLM_MODEL=${LIGHTRAG_LLM_MODEL}
EXTRACT_LLM_MODEL=${LIGHTRAG_EXTRACT_LLM_MODEL}
KEYWORD_LLM_MODEL=${LIGHTRAG_KEYWORD_LLM_MODEL}
QUERY_LLM_MODEL=${LIGHTRAG_QUERY_LLM_MODEL}
```

If a role-specific variable is unset, Atlas should omit it and let LightRAG fall back to `LLM_MODEL`.

Atlas should also make LightRAG query-time rerank behavior explicit. In rag-showcase,
LightRAG's Jina rerank client called Atlas's TEI reranker with an incompatible payload
and TEI returned `422 missing field texts`. The local fix was to disable LightRAG
query rerank and lower query fanout for graph-rag.

## Recommended Atlas Change

Add Atlas service inputs for the native LightRAG role variables:

- `LIGHTRAG_EXTRACT_LLM_MODEL`
- `LIGHTRAG_KEYWORD_LLM_MODEL`
- `LIGHTRAG_QUERY_LLM_MODEL`
- `LIGHTRAG_EXTRACT_LLM_BINDING`
- `LIGHTRAG_KEYWORD_LLM_BINDING`
- `LIGHTRAG_QUERY_LLM_BINDING`
- `LIGHTRAG_EXTRACT_LLM_BINDING_HOST`
- `LIGHTRAG_KEYWORD_LLM_BINDING_HOST`
- `LIGHTRAG_QUERY_LLM_BINDING_HOST`
- `LIGHTRAG_EXTRACT_LLM_BINDING_API_KEY`
- `LIGHTRAG_KEYWORD_LLM_BINDING_API_KEY`
- `LIGHTRAG_QUERY_LLM_BINDING_API_KEY`
- `LIGHTRAG_EXTRACT_MAX_ASYNC_LLM`
- `LIGHTRAG_KEYWORD_MAX_ASYNC_LLM`
- `LIGHTRAG_QUERY_MAX_ASYNC_LLM`
- `LIGHTRAG_EXTRACT_LLM_TIMEOUT`
- `LIGHTRAG_KEYWORD_LLM_TIMEOUT`
- `LIGHTRAG_QUERY_LLM_TIMEOUT`
- `LIGHTRAG_QUERY_ENABLE_RERANK`
- `LIGHTRAG_QUERY_TOP_K`
- `LIGHTRAG_QUERY_CHUNK_TOP_K`
- `LIGHTRAG_QUERY_MAX_TOTAL_TOKENS`

Then map them to LightRAG's native runtime names in the `lightrag` container:

```yaml
environment:
  EXTRACT_LLM_MODEL: ${LIGHTRAG_EXTRACT_LLM_MODEL:-}
  KEYWORD_LLM_MODEL: ${LIGHTRAG_KEYWORD_LLM_MODEL:-}
  QUERY_LLM_MODEL: ${LIGHTRAG_QUERY_LLM_MODEL:-}
  EXTRACT_LLM_BINDING: ${LIGHTRAG_EXTRACT_LLM_BINDING:-}
  KEYWORD_LLM_BINDING: ${LIGHTRAG_KEYWORD_LLM_BINDING:-}
  QUERY_LLM_BINDING: ${LIGHTRAG_QUERY_LLM_BINDING:-}
  EXTRACT_LLM_BINDING_HOST: ${LIGHTRAG_EXTRACT_LLM_BINDING_HOST:-}
  KEYWORD_LLM_BINDING_HOST: ${LIGHTRAG_KEYWORD_LLM_BINDING_HOST:-}
  QUERY_LLM_BINDING_HOST: ${LIGHTRAG_QUERY_LLM_BINDING_HOST:-}
```

Use the exact LightRAG native names in the runtime container. The init container can continue writing the base `LLM_MODEL` for backward compatibility.

For reranking, Atlas has three viable options:

1. Provide a LightRAG-compatible adapter for the TEI reranker payload.
2. Select a LightRAG rerank binding whose payload matches the configured service.
3. Default LightRAG query rerank off when wiring Atlas TEI directly, and document how to re-enable it.

## Defaults

Atlas should not hard-code `mistral-small3.2:24b` globally because Atlas is a reusable platform. It should expose the knobs and keep current behavior when the knobs are unset.

For a local Ollama profile, Atlas may document this recommended profile:

- `EXTRACT`: `mistral-small3.2:24b`
- `KEYWORD`: `mistral-small3.2:24b`
- `QUERY`: project-selected answer model

This gives graph extraction a cheaper, non-thinking model without forcing every Atlas deployment to use that model.

## Validation

Atlas should add a focused integration test or smoke script that:

1. Starts LightRAG with `LIGHTRAG_LLM_MODEL=qwen3.6:latest` and `LIGHTRAG_EXTRACT_LLM_MODEL=mistral-small3.2:24b`.
2. Inserts one small document.
3. Verifies the extraction call is sent to `mistral-small3.2:24b`.
4. Verifies query calls use `QUERY_LLM_MODEL` when set.
5. Verifies role variables omitted from config fall back to `LLM_MODEL`.
6. Verifies LightRAG query rerank is either disabled or calls a compatible reranker endpoint.

The most reliable assertion is request-level observation through LiteLLM logs, an Ollama proxy, or a mocked OpenAI-compatible endpoint that records the requested `model` field.

## Rag-Showcase Configuration

Rag-showcase now sets Atlas's public inputs in `infra/.env` during
`scripts/setup-overlay.sh`:

```dotenv
LIGHTRAG_EMBEDDING_MODEL=nomic-embed-text
LIGHTRAG_EXTRACT_LLM_MODEL=mistral-small3.2:24b
LIGHTRAG_KEYWORD_LLM_MODEL=mistral-small3.2:24b
LIGHTRAG_QUERY_LLM_MODEL=mistral-small3.2:24b
LIGHTRAG_EXTRACT_MAX_ASYNC_LLM=1
LIGHTRAG_EXTRACT_LLM_TIMEOUT=900
```

Those defaults are written only when the variables are unset, so operators can
choose different models or provider sources without editing the compose overlay.

The rag-showcase graph wrapper also sends these `/query` defaults:

```dotenv
LIGHTRAG_QUERY_ENABLE_RERANK=false
LIGHTRAG_QUERY_TOP_K=10
LIGHTRAG_QUERY_CHUNK_TOP_K=5
LIGHTRAG_QUERY_MAX_TOTAL_TOKENS=12000
```

Those are plugin-side request parameters rather than LightRAG container settings.
They avoid the TEI rerank mismatch and keep graph query prompts bounded.

## Acceptance Criteria

- Existing Atlas deployments remain compatible when role-specific variables are unset.
- LightRAG role variables are visible in the rendered compose/runtime environment.
- Extraction can be configured to use a non-reasoning model independently of query answering.
- A one-document graph build proves extraction requests use the configured extraction model.
- A graph query returns a substantive answer without TEI rerank 422 retries.
- Atlas docs explain the local Ollama recommendation and why extraction should use a non-reasoning model.
