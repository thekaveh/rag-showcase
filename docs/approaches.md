# 3.1 RAG Approach Internals

This document is the canonical guide to how each approach in rag-showcase works,
what it depends on, what can be tuned, and how it performed in the committed
2026-07-03 live dataset-ladder run.

The important terminology distinction:

- **Hybrid retrieval** means combining keyword search and dense vector search over
  chunks, then optionally reranking the chunk candidates.
- **Graph RAG** means querying an extracted knowledge graph of entities and
  relationships, here through Atlas's LightRAG service.

Therefore, `hybrid-rag` is not a graph-RAG approach. It is a text/chunk retrieval
approach with BM25 + dense retrieval and TEI reranking.

## 1. Shared Invocation Model

All six canonical approaches and the explicit experimental lazy graph route are mounted under the RAG plugin's shared
`/rag/<approach>/v1/chat/completions` root inside the Atlas backend container.
[`../backend_plugins/rag/plugin.yml`](../backend_plugins/rag/plugin.yml) declares
that `/rag` root, `/rag/health`, inherited Kong auth, typed configuration, and
the plugin's service dependencies. Atlas validates the manifest in consumer
doctor and again before loading the plugin.

The backend routes are declared as Atlas-managed LiteLLM model aliases, so Open WebUI and
the comparison harness invoke every approach through LiteLLM's common
`/v1/chat/completions` surface rather than calling the backend directly. Named
flavors such as `graph-rag-wide` point at the same base route and are resolved
from the incoming request model. See
[`approach-flavor-tuning.md`](approach-flavor-tuning.md) for the current flavor
manifest and benchmark invocation rules.

All approaches use the same ingested corpus and the same response wrapper:

1. Documents are loaded from the selected corpus directory.
2. Documents are chunked by Docling when configured, otherwise by the fallback
   800-character / 100-character-overlap chunker.
3. Base chunks are embedded and stored in Weaviate collection `RagBase`.
4. Context-prefixed chunks are generated, embedded, and stored in `RagContextual`.
5. Full source text is uploaded to LightRAG so it can build its own graph index.
6. Each approach returns a normalized answer, source block, and metrics footer.

### 1.1 Shared Model Roles

The selectable Open WebUI model name is the approach alias, not necessarily the
underlying LLM. The approach then calls one or more configured roles.

| Role | Default model | Used by | Notes |
|---|---|---|---|
| `embed` | `nomic-embed-text` | Weaviate-backed retrieval and the agent vector tool | Same embedding role across chunk-based approaches for fair vector comparison. |
| `light_gen` | `qwen3.6:latest` | `vanilla-rag`, `hybrid-rag`, `contextual-rag` | Shared final answer model for chunk-based approaches. |
| `contextual_blurb` | `qwen3.6:latest` | `contextual-rag` ingest | Generates short context blurbs before embedding contextual chunks. |
| `agentic` | `qwen3.6:latest` | `agentic-rag` | Controls the ReAct loop and tool selection. |
| LightRAG EXTRACT | `mistral-small3.2:24b` setup default | `graph-rag`; graph tool inside `agentic-rag` | Atlas-owned role for entity and relationship extraction. |
| LightRAG KEYWORD | `mistral-small3.2:24b` setup default | `graph-rag`; graph tool inside `agentic-rag` | Atlas-owned role for LightRAG keyword/query decomposition. |
| LightRAG QUERY | `mistral-small3.2:24b` setup default | `graph-rag`; graph tool inside `agentic-rag` | Atlas-owned role for final LightRAG graph answers. |
| n8n classifier | `qwen3.6:latest` | `n8n-adaptive-rag` | Workflow-level simple/complex classifier. |
| Lazy graph query | `nomic-embed-text` + `qwen3.6:latest` | experimental `lazy-graph-rag` | Shared embedding and final generation; concept indexing/traversal is LLM-free. |

Atlas's model catalog applies `request_defaults: {think: false}` to
`qwen3.6:latest`. The setting is scoped to that catalog entry, not injected by
the approach plugin or applied globally. If a role is changed to a different
local or cloud model, Atlas resolves that model's own adapter, capabilities, and
request defaults.

The full evaluation protocol, including judge models and result aggregation, is
documented in [`evaluation-methodology.md`](evaluation-methodology.md).

## 2. Current Measured Results

The current committed live run measured three dataset-ladder rungs. The table
below shows the six canonical approaches only; named flavors are ranked separately
in [`dataset-complexity-report.md`](dataset-complexity-report.md).

| Approach | Baseline curated | Graph-native | Cyber threat intel | Direction |
|---|---:|---:|---:|---|
| `vanilla-rag` | 4.25 | 3.38 | 3.08 | Strong simple baseline; loses ground as relation/path constraints grow. |
| `hybrid-rag` | 4.08 | 3.88 | 2.50 | Reliable text retriever; high-recall flavor improves graph-native aggregate. |
| `contextual-rag` | 4.08 | **3.94** | **3.17** | Best canonical default across the harder rungs. |
| `graph-rag` | 3.42 | 2.75 | 1.92 | Operational end to end, but current query settings are uneven. |
| `agentic-rag` | 2.67 | 2.62 | 2.00 | Step-limited and latency-heavy on complex prompts. |
| `n8n-adaptive-rag` | 4.25 | 3.56 | 3.08 | Very fast, inherits route-map quality. |

Snapshot files:

- Baseline matrix: [`results/live-2026-07-03-baseline_curated-matrix.json`](results/live-2026-07-03-baseline_curated-matrix.json)
- Baseline judgments: [`results/live-2026-07-03-baseline_curated-judgments.json`](results/live-2026-07-03-baseline_curated-judgments.json)
- Graph-native matrix: [`results/live-2026-07-03-graph_native-matrix.json`](results/live-2026-07-03-graph_native-matrix.json)
- Graph-native judgments: [`results/live-2026-07-03-graph_native-judgments.json`](results/live-2026-07-03-graph_native-judgments.json)
- Cyber matrix: [`results/live-2026-07-03-cyber_threat_intel-matrix.json`](results/live-2026-07-03-cyber_threat_intel-matrix.json)
- Cyber judgments: [`results/live-2026-07-03-cyber_threat_intel-judgments.json`](results/live-2026-07-03-cyber_threat_intel-judgments.json)

## 3. `vanilla-rag`

### 3.1 Purpose

`vanilla-rag` is the control path: pure dense vector retrieval over plain chunks,
followed by one answer-generation call.

### 3.2 Internal Steps

1. Read the latest user message.
2. Embed the question through LiteLLM.
3. Search Weaviate collection `RagBase` with `near_vector`.
4. Retrieve the top `K=5` chunks.
5. Stuff those chunks into the shared answer prompt.
6. Call the `light_gen` model once.
7. Return the answer plus the retrieved chunk titles/snippets.

### 3.3 Dependencies

- LiteLLM embedding route.
- Weaviate collection `RagBase`.
- LiteLLM chat route for `light_gen`.

### 3.4 Models Used

- Query embedding: `embed` role, default `nomic-embed-text`.
- Answer generation: `light_gen` role, default `qwen3.6:latest`.
- Judge evaluation: outside the approach, `compare/judge.py` scores stored
  answers with `qwen3.6:latest` and `gemma4:31b`.

### 3.5 Tuning Surface

| Knob | Current value | Exposed as env? | Notes |
|---|---:|---|---|
| `K` | 5 | Via flavor | Default 5 in `vanilla.py`; overridable per flavor via `k` (e.g. `vanilla-rag-wide` uses 8). |
| Collection | `RagBase` | No | Uses plain chunks only. |
| Chunk size / overlap | 800 / 100 | No | In ingest fallback and Docling request. |
| Prompt template | shared `stuff` prompt | No | Shared with hybrid/contextual. |
| Generation model | `roles.yaml` `light_gen` | Yes, via roles file | Per-model request defaults come from Atlas's model catalog. |

### 3.6 Observed Behavior

Fast and surprisingly competitive on simple fact and exact-context questions. It
declined on the graph-native corpus because dense top-k alone does not reliably
assemble relationship chains or cross-document entity links.

## 4. `hybrid-rag`

### 4.1 Purpose

`hybrid-rag` tests whether better text retrieval is enough: it combines keyword
and dense retrieval over plain chunks, then reranks candidates before generation.
It does not query LightRAG or use extracted graph entities/relations.

### 4.2 Internal Steps

1. Read the latest user message.
2. Embed the question through LiteLLM.
3. Search Weaviate collection `RagBase` with native hybrid search:
   BM25 keyword matching + dense vector search.
4. Use Weaviate's default relative score fusion with `alpha=0.5`.
5. Retrieve `RETRIEVE_K=20` candidates.
6. Send those candidates to the TEI cross-encoder reranker.
7. Keep `TOP_N=5` reranked chunks.
8. Stuff those chunks into the shared answer prompt.
9. Call the `light_gen` model once.
10. Return the answer plus reranked sources and TEI scores.

### 4.3 Dependencies

- LiteLLM embedding route.
- Weaviate collection `RagBase`.
- Weaviate BM25 + vector indexes.
- TEI reranker endpoint.
- LiteLLM chat route for `light_gen`.

### 4.4 Models Used

- Query embedding: `embed` role, default `nomic-embed-text`.
- Reranking: Atlas TEI reranker service, default endpoint
  `http://tei-reranker:80`.
- Answer generation: `light_gen` role, default `qwen3.6:latest`.
- Judge evaluation: outside the approach, `compare/judge.py` scores stored
  answers with `qwen3.6:latest` and `gemma4:31b`.

### 4.5 Tuning Surface

| Knob | Current value | Exposed as env? | Notes |
|---|---:|---|---|
| `RETRIEVE_K` | 20 | Via flavor | Candidate pool before rerank; overridable via `retrieve_k` (e.g. `hybrid-rag-high-recall` uses 40). |
| `TOP_N` | 5 | Via flavor | Final chunks sent to generation; overridable via `top_n` (e.g. `hybrid-rag-high-recall` uses 8). |
| Hybrid `alpha` | 0.5 | Via flavor | Equal BM25/vector weighting in `vectors.search_hybrid`; overridable via `alpha`. |
| Rerank | on | Via flavor | TEI cross-encoder rerank; disable via `rerank: false` (e.g. `hybrid-rag-fast`). |
| Fusion type | Weaviate default | No | Current code relies on Weaviate default relative score fusion. |
| TEI endpoint | `http://tei-reranker:80` | Yes, `TEI_RERANKER_ENDPOINT` | Reranker quality/model can materially affect results. |
| Collection | `RagBase` | No | Plain chunks only. |

### 4.6 Observed Behavior

The high-recall hybrid flavor won the graph-native corpus at 4.25/5, while the
canonical `hybrid-rag` route scored 3.88/5. That does not mean it used a graph;
it means keyword+dense retrieval plus reranking found the right supporting chunks
more reliably than the current LightRAG query configuration.

## 5. `contextual-rag`

### 5.1 Purpose

`contextual-rag` follows Anthropic-style Contextual Retrieval. It enriches each
chunk at ingest time with a short context blurb, then uses the same hybrid+rerank
query path as `hybrid-rag`.

### 5.2 Internal Steps

Ingest-time:

1. Chunk each document.
2. For each chunk, send a 6000-character document window centered on the chunk
   (document-prefix fallback when the chunk isn't found verbatim) plus the chunk
   to the `contextual_blurb` model.
3. Generate a 1-2 sentence context blurb.
4. Prefix the chunk with that blurb.
5. Embed and store the result in Weaviate collection `RagContextual`.

Query-time:

1. Embed the user question.
2. Search `RagContextual` with Weaviate hybrid search.
3. Retrieve `RETRIEVE_K=20` candidates.
4. Rerank with TEI.
5. Keep `TOP_N=5`.
6. Stuff selected context-prefixed chunks into the shared prompt.
7. Call `light_gen` once.

### 5.3 Dependencies

- LiteLLM embedding route.
- LiteLLM chat route for `contextual_blurb` at ingest time.
- Weaviate collection `RagContextual`.
- TEI reranker endpoint.
- LiteLLM chat route for `light_gen`.

### 5.4 Models Used

- Ingest-time contextualization: `contextual_blurb` role, default
  `qwen3.6:latest`.
- Query embedding: `embed` role, default `nomic-embed-text`.
- Reranking: Atlas TEI reranker service, default endpoint
  `http://tei-reranker:80`.
- Answer generation: `light_gen` role, default `qwen3.6:latest`.
- Judge evaluation: outside the approach, `compare/judge.py` scores stored
  answers with `qwen3.6:latest` and `gemma4:31b`.

### 5.5 Tuning Surface

| Knob | Current value | Exposed as env? | Notes |
|---|---:|---|---|
| Context blurb model | `roles.yaml` `contextual_blurb` | Yes, via roles file | Quality/speed tradeoff. |
| Context prompt | fixed | No | Prompt asks for 1-2 situating sentences. |
| Document context cap | 6000 chars | No | `_DOC_WINDOW` in `contextual.py`; window centered on the chunk, prefix fallback. |
| `RETRIEVE_K` | 20 | Via flavor | Same as `hybrid-rag`; overridable via `retrieve_k` (e.g. `contextual-rag-high-recall` uses 40). |
| `TOP_N` | 5 | Via flavor | Same as `hybrid-rag`; overridable via `top_n` (e.g. `contextual-rag-high-recall` uses 8). |
| Hybrid `alpha` | 0.5 | Via flavor | Same search helper as `hybrid-rag`; overridable via `alpha`. |
| Rerank | on | Via flavor | Same TEI rerank as `hybrid-rag`; disable via `rerank: false`. |

### 5.6 Observed Behavior

This was the strongest canonical default on the harder rungs: the best canonical
approach on graph-native (3.94, second overall) and on cyber threat intel (3.17,
second overall), while only mid-pack on the simplest baseline corpus (4.08, where
`vanilla-rag-wide` led at 4.42). It benefits when chunks are ambiguous without their
document-level context.

## 6. `graph-rag`

### 6.1 Purpose

`graph-rag` delegates query answering to Atlas's LightRAG service. LightRAG builds
a knowledge graph during indexing and queries over extracted entities,
relationships, and vector context.

### 6.2 Internal Steps

Ingest-time:

1. Full document text is uploaded to LightRAG.
2. LightRAG chunks and extracts entities/relationships.
3. LightRAG stores graph data through its configured stores, including Neo4j.
4. LightRAG embeds graph/chunk artifacts for query-time retrieval.

Query-time:

1. The wrapper sends the user question to LightRAG `/query`.
2. The query mode defaults to `hybrid`, overridable per flavor via `mode` (e.g.
   `graph-rag-fast` uses `local`).
3. The query payload includes `enable_rerank`, `top_k`, `chunk_top_k`, and
   `max_total_tokens`.
4. LightRAG performs its graph/vector retrieval and generation internally.
5. The wrapper returns LightRAG's answer with a single source entry labeled
   "LightRAG knowledge graph".

### 6.3 Dependencies

- Atlas LightRAG service.
- LightRAG's configured graph/vector stores, including Neo4j.
- LightRAG role models for EXTRACT, KEYWORD, and QUERY.
- LightRAG embedding model.

### 6.4 Models Used

- Graph extraction: Atlas LightRAG EXTRACT role, setup default
  `mistral-small3.2:24b`.
- Graph keyword/query decomposition: Atlas LightRAG KEYWORD role, setup default
  `mistral-small3.2:24b`.
- Graph answer generation: Atlas LightRAG QUERY role, setup default
  `mistral-small3.2:24b`.
- LightRAG embeddings: setup default `nomic-embed-text`.
- Judge evaluation: outside the approach, `compare/judge.py` scores stored
  answers with `qwen3.6:latest` and `gemma4:31b`.

These LightRAG role models are configured through Atlas `LIGHTRAG_*` inputs, not
through this plugin's `roles.yaml` `extraction` entry. The shipped default uses a
non-reasoning Mistral model because LightRAG extraction makes many structured
entity/relationship calls and reasoning-model chain-of-thought overhead was too
slow for that phase.

### 6.5 Tuning Surface

| Knob | Current value | Exposed as env? | Notes |
|---|---:|---|---|
| Query mode | `hybrid` | Via flavor | Default `hybrid` in `graph.py`; overridable via `mode` (`graph-rag-fast` uses `local`). |
| `LIGHTRAG_QUERY_ENABLE_RERANK` | `false` | Yes | Disabled because current TEI payload is incompatible with LightRAG's Jina-style rerank client. |
| `LIGHTRAG_QUERY_TOP_K` | 10 | Yes | Knowledge-graph candidate fanout. |
| `LIGHTRAG_QUERY_CHUNK_TOP_K` | 5 | Yes | Chunk context fanout. |
| `LIGHTRAG_QUERY_MAX_TOTAL_TOKENS` | 12000 | Yes | Query prompt/context budget. |
| `LIGHTRAG_EXTRACT_LLM_MODEL` | `mistral-small3.2:24b` | Yes, Atlas `.env` | Extraction model choice has large quality/latency impact. |
| `LIGHTRAG_KEYWORD_LLM_MODEL` | `mistral-small3.2:24b` | Yes, Atlas `.env` | Keyword/query decomposition role. |
| `LIGHTRAG_QUERY_LLM_MODEL` | `mistral-small3.2:24b` | Yes, Atlas `.env` | Final graph answer model. |
| `LIGHTRAG_EXTRACT_MAX_ASYNC_LLM` | 1 | Yes, Atlas `.env` | Stability vs throughput. |
| `LIGHTRAG_EXTRACT_LLM_TIMEOUT` | 900 | Yes, Atlas `.env` | Prevents slow extraction calls from failing too early. |
| Ollama role context caps | 8192 defaults when native Ollama binding is used | Yes | Passed through overlay as `*_OLLAMA_LLM_NUM_CTX`. |

### 6.6 Observed Behavior

`graph-rag` is now operational: it indexed all three measured datasets and answered
every query cell. It still did not win any dataset on aggregate. The `graph-rag-fast`
flavor was stronger than default and won individual baseline and graph-native
questions, while `graph-rag-wide` frequently returned truncated answers and ranked
last. The weakest graph scores were broader synthesis and cyber path questions
where current LightRAG query settings under-synthesized compared with
hybrid/contextual chunk retrieval.

### 6.7 Untested Fine-Tuning Opportunities

The current results should not be read as the ceiling for LightRAG. We have not
yet swept:

- LightRAG query modes beyond the `local`/`hybrid` already sampled by flavors.
- `top_k`, `chunk_top_k`, and `max_total_tokens` swept systematically.
- Re-enabling rerank with a LightRAG-compatible reranker adapter.
- Using a stronger QUERY model while keeping a cheaper EXTRACT model.
- Different graph extraction models and extraction concurrency.
- More graph-native datasets with harder relationship/path constraints.

## 7. `agentic-rag`

### 7.1 Purpose

`agentic-rag` tests whether an LLM-controlled ReAct loop can decide when to use
vector search or graph search, instead of following a fixed retrieval path.

### 7.2 Internal Steps

1. Start with a system prompt telling the model to gather evidence before answering.
2. Give the model two tools:
   - `search_vectors(query)`: hybrid search over `RagBase`.
   - `query_graph(query)`: LightRAG query in hybrid mode.
3. Run up to `MAX_STEPS=4` model turns.
4. For each tool call, execute the tool and append an observation.
5. Stop when the model returns an answer with no tool calls.
6. If the loop exhausts, return the explicit MAX_STEPS fallback.
7. Include the tool trace as the source block.

### 7.3 Dependencies

- LiteLLM chat route for `agentic`.
- LiteLLM embeddings for vector tool calls.
- Weaviate `RagBase`.
- LightRAG for graph tool calls.

### 7.4 Models Used

- Agent controller: `agentic` role, default `qwen3.6:latest`.
- Vector tool embedding: `embed` role, default `nomic-embed-text`.
- Graph tool: LightRAG EXTRACT/KEYWORD/QUERY roles, setup default
  `mistral-small3.2:24b`.
- Judge evaluation: outside the approach, `compare/judge.py` scores stored
  answers with `qwen3.6:latest` and `gemma4:31b`.

### 7.5 Tuning Surface

| Knob | Current value | Exposed as env? | Notes |
|---|---:|---|---|
| `MAX_STEPS` | 4 | Via flavor | Major quality limiter; overridable via `max_steps` (e.g. `agentic-rag-deeper` uses 8). |
| Vector tool candidate count | 5 | Via flavor | Default 5; overridable via `vector_top_k` (e.g. `agentic-rag-deeper` uses 8). |
| Graph tool mode | `hybrid` | Via flavor | Default `hybrid`; overridable via `graph_mode`. |
| Tool descriptions | fixed | No | Affects model's routing/tool choice. |
| System prompt | fixed | No | Affects whether it searches, answers early, or loops. |
| Agent model | `roles.yaml` `agentic` | Yes, via roles file | Larger/cheaper/non-reasoning choices change behavior. |

### 7.6 Observed Behavior

The agent occasionally won individual multi-step questions, but the hard step
limit caused frequent incomplete answers. It also became the slowest approach on
graph-native because each tool loop adds model/tool calls.

## 8. `n8n-adaptive-rag`

### 8.1 Purpose

`n8n-adaptive-rag` demonstrates low-code routing. It classifies the query as simple
or complex, sends it to another approach, then normalizes the response.

### 8.2 Internal Steps

1. The plugin POSTs `{ "query": ... }` to the n8n production webhook.
2. n8n calls LiteLLM to classify the query as `simple` or `complex`.
3. The workflow routes:
   - `simple` -> `vanilla-rag`
   - `complex` -> `agentic-rag`
4. n8n calls the selected backend approach route.
5. n8n shapes `{ answer, route, approach }`.
6. The plugin wraps that response in the common OpenAI-compatible output format.

### 8.3 Dependencies

- n8n container and active `adaptive-rag` workflow.
- LiteLLM from inside n8n for classification.
- Atlas backend approach routes.

### 8.4 Models Used

- Workflow classifier: `qwen3.6:latest` in
  `n8n/adaptive-rag.workflow.json`.
- Downstream answer model: inherited from the selected route. In the current
  workflow, `simple` routes to `vanilla-rag` and `complex` routes to
  `agentic-rag`.
- Judge evaluation: outside the approach, `compare/judge.py` scores stored
  answers with `qwen3.6:latest` and `gemma4:31b`.

### 8.5 Tuning Surface

| Knob | Current value | Exposed as env? | Notes |
|---|---:|---|---|
| Webhook URL | `http://n8n:5678/webhook/adaptive-rag` | Yes, `N8N_ADAPTIVE_WEBHOOK_URL` | Plugin wrapper setting. |
| Classifier model | `qwen3.6:latest` | Workflow JSON | Change in `n8n/adaptive-rag.workflow.json`. |
| Classifier prompt | fixed | Workflow JSON | Determines simple/complex routing. |
| Route map | simple -> vanilla, complex -> agentic | Workflow JSON | Could route graph-native questions to hybrid or graph instead. |
| Approach-call timeout | 175000 ms | Workflow JSON | Workflow HTTP node timeout. |
| Workflow activation/import | startup script | Yes, via checked-in workflow | `start-all.sh` imports active workflow and restarts n8n. |

### 8.6 Observed Behavior

Very fast in the measured runs because it often delegates to `vanilla-rag` and
benefits from warm caches. It is not a better retriever by itself; its quality is
bounded by the classifier and selected downstream route.

## 9. Experimental `lazy-graph-rag`

`lazy-graph-rag` is a seventh, explicitly selected prototype. It builds a
deterministic concept/co-occurrence graph from the existing `RagBase` chunks,
uses hybrid vector retrieval for seeds, expands concepts under a hard relevance
budget, and performs one shared `light_gen` call over the selected chunks. It
does not use LightRAG or Neo4j and it makes no LLM calls while indexing.

The graph is persisted in a named Compose volume and invalidated by a corpus
content fingerprint. Fast, balanced, and wide flavors tune
`relevance_budget`, `seed_k`, `max_context_chunks`, and graph density. It is
excluded from the six canonical defaults and has no committed measured score.
See [`lazy-graph-rag.md`](lazy-graph-rag.md) for its full design, phases,
metadata contract, limitations, and Atlas #565 evaluation gate.

## 10. Cross-Approach Comparison

| Question | Best current answer |
|---|---|
| Cheapest useful baseline? | `vanilla-rag` |
| Best current default? | `contextual-rag` |
| Best measured graph-native aggregate? | `hybrid-rag-high-recall` flavor; `contextual-rag` among canonical defaults |
| True knowledge-graph path? | `graph-rag` |
| Best place to test tool-use/multi-hop planning? | `agentic-rag` |
| Best low-code routing demonstration? | `n8n-adaptive-rag` |
| Experimental LLM-free graph expansion? | `lazy-graph-rag` (not yet ranked) |

## 11. Tuning Priorities

The current results are a measured baseline, not the end of the search space.
The highest-leverage tuning work is:

1. Run a systematic `graph-rag` mode/fanout sweep — `mode`, `top_k`, `chunk_top_k`,
   and `max_total_tokens` are already flavor-overridable.
2. Fix or adapt LightRAG query rerank so reranking can be evaluated instead of
   disabled.
3. Sweep `hybrid-rag` and `contextual-rag` `retrieve_k`, `top_n`, and hybrid
   `alpha` by dataset — all already flavor-overridable.
4. Sweep `agentic-rag` `max_steps` and `vector_top_k` (already flavor-overridable)
   and improve the tool prompt.
5. Tune the n8n route map so graph-native queries can route to `hybrid-rag` or
   `graph-rag`, not only `vanilla-rag` or `agentic-rag`.
6. Treat chunk size/overlap and contextual blurb model/prompt as dataset-level
   tuning variables.
