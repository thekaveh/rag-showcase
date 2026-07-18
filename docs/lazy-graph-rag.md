# 3.3 Experimental Lazy Graph RAG

`lazy-graph-rag` is an **experimental** seventh approach inspired by the public
LazyGraphRAG design direction. It is a repo-native approximation, not Microsoft
GraphRAG code and not a claim of implementation parity. It is registered for
explicit testing but excluded from the six-approach default comparison. Its
concept indexing and graph traversal are LLM-free.

The prototype is now measured in the committed 2026-07-17 dataset ladder. It
participated beside all six canonical approaches on baseline, graph-native, and
MITRE ATT&CK cyber-threat corpora. All 20 lazy-graph cells succeeded. The result
supports keeping the approach: it tied for third on baseline, won graph-native,
and tied for second on cyber while retaining low latency. It remains experimental and off by default
because its untyped co-occurrence graph is a useful approximation, not a
general-purpose knowledge graph.

## 1. Why It Is a Separate Approach

`lazy-graph-rag` occupies a different point from the existing retrieval paths:

| Approach | Index-time structure | Query-time behavior |
|---|---|---|
| `hybrid-rag` | Weaviate chunk vectors + BM25 | Dense/lexical retrieval, TEI rerank, generation |
| `graph-rag` | LightRAG LLM-extracted entities and relationships in Neo4j/vector stores | LightRAG graph/vector retrieval and generation |
| `agentic-rag` | Reuses vector and LightRAG indexes | An LLM-controlled ReAct loop chooses retrieval tools |
| `lazy-graph-rag` | Deterministic concept/co-occurrence graph over existing chunks | Vector seeds followed by budgeted concept expansion and one generation call |

It is not a `graph-rag` flavor because it does not query LightRAG, does not use
LightRAG's extracted knowledge graph, and has a separate index lifecycle. It is
not a `hybrid-rag` flavor because graph traversal changes which evidence enters
the final context. It is not agentic: graph expansion is deterministic and
bounded rather than selected by an LLM loop.

## 2. Components and Data Flow

The implementation lives in:

- `backend_plugins/rag/common/lazy_graph.py`: extraction, graph construction,
  serialization, cache validation, and budgeted traversal;
- `backend_plugins/rag/approaches/lazy.py`: OpenAI-compatible endpoint;
- `backend_plugins/rag/common/vectors.py`: complete `RagBase` chunk snapshot;
- `backend_plugins/rag/flavors.yaml`: runtime flavor parameters;
- `compare/flavors.yaml`: explicit benchmark selection metadata;
- `atlas.consumer.yml`: Atlas/LiteLLM model aliases.

The route remains the same type of backend plugin endpoint as every other
approach:

```text
POST /rag/lazy-graph-rag/v1/chat/completions
```

Atlas exposes `lazy-graph-rag`, `lazy-graph-rag-fast`,
`lazy-graph-rag-balanced`, and `lazy-graph-rag-wide` through LiteLLM and Open
WebUI. They carry `experimental: true` metadata. None is included when the
comparison harness expands `default`.

## 3. Index Construction

The first query for a corpus performs these steps:

1. Read a deterministic snapshot of all chunks in Weaviate collection `RagBase`.
2. Compute a SHA-256 **content fingerprint** over the index algorithm version,
   chunk titles, and chunk text.
3. Load the density-specific cache under `/data/lazy-graph-rag/` when its version
   and fingerprint match, for example `RagBase_graph_native.concepts-24.json`.
4. Otherwise extract concepts using deterministic token, identifier, and
   capitalized-phrase rules. No LLM is called.
5. Create concept-to-chunk memberships.
6. Add weighted undirected edges for concepts that co-occur in a chunk.
7. Atomically replace that density-specific cache file in the
   `lazy-graph-cache` Compose volume.

The complete chunk snapshot is fingerprinted on each query, so an ingest that
changes content invalidates the graph even when the chunk count is unchanged.
Each `max_concepts_per_chunk` value gets an independent cache namespace, so
switching between fast, balanced, and wide flavors does not evict another
density. The named volume preserves matching indexes across backend restarts. A
cold volume reset removes the caches and forces rebuilds. Corrupt or incompatible
cache files are ignored and replaced. A one-shot Compose initializer assigns the
named volume to Atlas's non-root backend user before the backend starts.

Index construction uses zero LLM calls. The response records cache hit/miss,
index duration, chunk/concept/edge counts, and `llm_index_calls: 0`.

## 4. Query Phases

1. Embed the question through the shared `embed` role.
2. Run Weaviate BM25+dense hybrid search to obtain `seed_k` chunks.
3. Extract concepts from the question and seed chunks with the same deterministic
   extractor used during indexing.
4. Traverse weighted concept neighbors using a priority queue.
5. Stop after at most `relevance_budget` visited concepts.
6. Score chunks from vector-seed rank and visited concept membership.
7. Keep at most `max_context_chunks` chunks.
8. Stuff the selected evidence into the shared prompt.
9. Generate once through the shared `light_gen` role.
10. Return the standard answer, source block, and metrics footer plus structured
    `rag_showcase.lazy_graph` provenance.

The normal query path therefore makes two LiteLLM calls: one embedding call and
one generation call. Concept extraction, graph construction, and traversal do
not call an LLM or cloud service.

## 5. Tuning and Flavors

| Alias | `relevance_budget` | `seed_k` | `max_context_chunks` | Concepts/chunk |
|---|---:|---:|---:|---:|
| `lazy-graph-rag` | 24 | 8 | 8 | 24 |
| `lazy-graph-rag-fast` | 8 | 4 | 4 | 16 |
| `lazy-graph-rag-balanced` | 24 | 8 | 8 | 24 |
| `lazy-graph-rag-wide` | 64 | 16 | 12 | 32 |

- `relevance_budget` is a hard cap on tested/expanded graph concepts.
- `seed_k` controls the initial vector/lexical evidence fanout.
- `max_context_chunks` caps final generation context.
- `max_concepts_per_chunk` controls graph density and cache size.

The last knob changes the generated lazy index but does not require source
corpus re-ingestion. Its flavor gets a distinct cache file at query time. Live
validation alternated base, fast, balanced, and wide calls and confirmed that
all three graph densities remained independently reusable.

Run an explicit comparison selection with:

```bash
MATRIX_MODELS=lazy-graph-rag-fast,lazy-graph-rag-balanced,lazy-graph-rag-wide \
  uv run python compare/run_matrix.py
```

## 6. Response and Evaluation Metadata

Non-streaming responses add a top-level `rag_showcase.lazy_graph` object while
preserving the OpenAI chat-completion body and common rendered footer. The
comparison collector stores this as `approach_metadata` rather than parsing it
from display text.

Recorded fields include:

- experimental status and cache hit/miss;
- index duration and graph size;
- relevance tests and configured budgets;
- zero index-time LLM calls;
- cache namespace.

The consumer-owned Atlas-backed matrix combines those operational fields with
cold/warm cache state, latency, Ragas state, judge-panel scores, errors, and
dataset/model/config provenance. Ragas and judge scores remain separate. The
current Atlas evaluator returns numeric faithfulness and answer relevancy with
explicit coverage; missing or failed metric rows are never replaced by judge
scores or numeric zeroes.

## 7. Measured Results

The 2026-07-17 run used the same Atlas ingestion revision, generation role,
embedding role, questions, and blinded judges for every approach. The complete
artifacts are under [`docs/results/`](results/) and the generated per-query view
is [`dataset-complexity-report.md`](dataset-complexity-report.md).

| Dataset | Lazy rank | Judge mean | Mean latency | Graph size | Result |
|---|---:|---:|---:|---|---|
| `baseline_curated` | tied 3/7 | 3.92 | 5.51 s | 30 chunks, 453 concepts, 7,523 edges | Competitive, but vanilla and hybrid retrieval led. |
| `graph_native` | 1/7 | 4.31 | 4.94 s | 10 chunks, 162 concepts, 2,475 edges | Won the aggregate and two individual questions. |
| `cyber_threat_intel` | tied 2/7 | 3.00 | 8.12 s | 66 chunks, 762 concepts, 13,949 edges | Competitive on relation-heavy prompts; contextual RAG led. |

Across the same rungs, default LightRAG averaged 12.61, 12.47, and 21.20 seconds;
agentic retrieval averaged 10.77, 29.11, and 41.86 seconds. Lazy graph made
exactly two model calls per query: one embedding and one final generation call.
It made zero index-time model calls.

Cold deterministic index construction was 0.019 seconds for 30 baseline chunks
and 0.028 seconds for 66 cyber chunks. The first end-to-end lazy calls include
embedding, retrieval, graph build, and generation; the graph build itself remains
negligible relative to model inference.
Subsequent fingerprint/cache checks took roughly 0.002-0.010 seconds. A separate
live flavor gate built base, fast, and wide graph densities, then confirmed warm
hits for base/balanced and fast without cross-flavor rebuild churn.

These numbers do not establish universal superiority. The cyber aggregate winner
was contextual RAG, and lazy graph lost several exact path questions where
typed entity/relation extraction or high-recall chunk retrieval produced better
evidence. The graph-native win nevertheless satisfies the prototype's keep criterion,
so the implementation remains available for explicit selection.

## 8. Limitations and Decision

- The concept extractor is intentionally lightweight; aliases, morphology, and
  domain-specific entity resolution are limited.
- Co-occurrence is evidence of proximity, not a typed factual relationship.
- The implementation currently uses the shared generation prompt rather than a
  claim-synthesis stage.
- The steady path still scans all chunk text to verify the content fingerprint.
- Results cover three bounded corpora and two local judges, not a broad benchmark.
- Objective Ragas coverage is unavailable until Atlas #596/#597 are fixed and
  this exact run is repeated.

**Decision:** retain the prototype as an experimental seventh approach, keep it
excluded from `default`, and continue measuring it. It beat existing approaches
on graph-native tasks and led the cyber aggregate without added index-time LLM
cost, so removal is not warranted. Promotion to a canonical default would require
more datasets, objective evaluator coverage, stronger concept/entity resolution,
and explicit typed-relation or community semantics.
