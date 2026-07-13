# 3.3 Experimental Lazy Graph RAG

`lazy-graph-rag` is an **experimental** seventh approach inspired by the public
LazyGraphRAG design direction. It is a repo-native approximation, not Microsoft
GraphRAG code and not a claim of implementation parity. It is registered for
explicit testing but excluded from the six-approach default comparison. Its
concept indexing and graph traversal are LLM-free.

The prototype is **not yet measured** in a committed dataset-ladder run. Atlas
currently has only the per-record Ragas endpoint, while the reusable matrix
runner required by showcase issue #24 is tracked upstream as
[Atlas #565](https://github.com/thekaveh/atlas/issues/565). Until that runner
lands, this page documents independently verified design and unit/integration
behavior rather than benchmark rankings.

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
3. Load `/data/lazy-graph-rag/RagBase.json` when its version and fingerprint
   match.
4. Otherwise extract concepts using deterministic token, identifier, and
   capitalized-phrase rules. No LLM is called.
5. Create concept-to-chunk memberships.
6. Add weighted undirected edges for concepts that co-occur in a chunk.
7. Atomically replace the cache file in the `lazy-graph-cache` Compose volume.

The complete chunk snapshot is fingerprinted on each query, so an ingest that
changes content invalidates the graph even when the chunk count is unchanged.
The named volume preserves matching indexes across backend restarts. A cold
volume reset removes the cache and forces a rebuild. Corrupt or incompatible
cache files are ignored and replaced.

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
corpus re-ingestion. Its flavor gets a distinct fingerprint-equivalent cache
build at query time. The current single cache namespace is replaced when a
different concept limit is selected; this is correct but can cause rebuild
churn when alternating flavors and is a prototype limitation.

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

Future Atlas matrix output must combine those operational fields with cold/warm
latency, Ragas evaluator-model metrics, judge-panel scores, errors, and dataset/
model/config provenance. Ragas and judge scores must remain separate.

## 7. Limitations and Evaluation Gate

- The concept extractor is intentionally lightweight; aliases, morphology, and
  domain-specific entity resolution are limited.
- Co-occurrence is evidence of proximity, not a typed factual relationship.
- Fetching all chunk text to verify the fingerprint adds steady-state overhead.
- Alternating concept-density flavors can rebuild the one cache namespace.
- The implementation currently uses the shared generation prompt rather than a
  claim-synthesis stage.
- No committed quality ranking, cold/warm benchmark, or cost comparison exists.

The prototype must remain experimental and off by default until Atlas #565
enables the same evidence-aware matrix used by the canonical approaches. A
future measured run must compare it with `graph-rag`, `hybrid-rag`, and
`agentic-rag` on graph-native rungs and report index time, cold/warm latency,
LLM calls, failures, Ragas metrics, judge quality, and ranking changes. If it
does not win any graph-native task or proves too costly or fragile, the correct
result is to document that outcome and keep it experimental.
