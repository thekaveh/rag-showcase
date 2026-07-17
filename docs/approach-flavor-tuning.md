# 3.2 RAG Approach Flavor Tuning

This guide explains how rag-showcase runs named tuning variants of its seven RAG
approaches without changing the canonical defaults.

## 1. Concept

The six stable approaches remain:

- `vanilla-rag`
- `hybrid-rag`
- `contextual-rag`
- `graph-rag`
- `agentic-rag`
- `n8n-adaptive-rag`

A **flavor** is a named model alias that points at a supported base route with
specific parameter overrides. For example, `graph-rag-wide` is still the
`graph-rag` backend route, but the request model selects Atlas's wider LightRAG
query profile.

This gives users a clean Open WebUI interface and gives the benchmark harness a
reproducible experiment surface.

The experimental `lazy-graph-rag` family follows the same alias mechanism but is
not part of the six canonical `default` profiles. It must be selected explicitly.

## 2. Open WebUI Invocation

After Atlas compiles `atlas.consumer.yml`, Open WebUI sees canonical approaches and
flavor aliases as selectable models. A user invokes a tuned LightRAG path by
selecting the alias:

```text
graph-rag-wide
```

That request is routed by LiteLLM to:

```text
http://backend:8000/rag/graph-rag/v1/chat/completions
```

The backend reads the incoming request model (`graph-rag-wide`), resolves its
base route from `backend_plugins/rag/flavors.yaml`, and passes that alias as the
LightRAG query profile. Atlas validates and materializes the profile registry;
the showcase no longer duplicates LightRAG mode/fanout values in its flavor file.

Users should not need to pass hidden JSON or prompt prefixes for normal tuning.
Named aliases are easier to discover, reproduce, compare, and document.

## 3. Configuration Files

The declarations are split by ownership and drift-tested:

- `backend_plugins/rag/flavors.yaml` maps aliases to showcase base routes and owns
  showcase-native parameters.
- `compare/flavors.yaml` controls host-side comparison expansion and metadata.
- `atlas.consumer.yml` declares every LiteLLM alias and owns
  `lightrag_query_profiles` for graph mode, fanout, token budget, and reranking.

The compose overlay sets:

```bash
RAG_FLAVORS_FILE=/app/plugins/rag/flavors.yaml
```

The comparison harness can use an alternate manifest with:

```bash
MATRIX_FLAVORS_FILE=path/to/flavors.yaml
```

## 4. Current Query-Time Flavors

| Alias | Base | What changes | Re-ingest? |
|---|---|---|---|
| `vanilla-rag-wide` | `vanilla-rag` | dense top-k `k=8` | No |
| `hybrid-rag-high-recall` | `hybrid-rag` | `retrieve_k=40`, `top_n=8` | No |
| `hybrid-rag-fast` | `hybrid-rag` | smaller pool, rerank disabled | No |
| `contextual-rag-high-recall` | `contextual-rag` | `retrieve_k=40`, `top_n=8` | No |
| `graph-rag-fast` | `graph-rag` | LightRAG `mode=local`, lower fanout | No |
| `graph-rag-wide` | `graph-rag` | LightRAG `top_k=30`, `chunk_top_k=12`, `max_total_tokens=24000` | No |
| `graph-rag-rerank` | `graph-rag` | canonical hybrid fanout plus Atlas LightRAG-to-TEI reranking | No |
| `agentic-rag-deeper` | `agentic-rag` | `max_steps=8`, vector tool top-k `8` | No |
| `n8n-adaptive-rag-default` | `n8n-adaptive-rag` | explicit alias for current workflow | No |
| `lazy-graph-rag-fast` | `lazy-graph-rag` | budgets `8/4/4` for relevance/seed/context | No source re-ingest; lazy index may rebuild |
| `lazy-graph-rag-balanced` | `lazy-graph-rag` | budgets `24/8/8` | No source re-ingest; lazy index may rebuild |
| `lazy-graph-rag-wide` | `lazy-graph-rag` | budgets `64/16/12` | No source re-ingest; lazy index may rebuild |

## 5. Benchmark Invocation

Run the current six defaults:

```bash
uv run python compare/run_matrix.py
```

Run defaults plus one flavor:

```bash
MATRIX_FLAVORS=default,graph-rag-wide uv run python compare/run_matrix.py
```

Run an exact model list:

```bash
MATRIX_MODELS=graph-rag-wide,hybrid-rag-high-recall uv run python compare/run_matrix.py
```

Run the experimental lazy graph family explicitly:

```bash
MATRIX_FLAVORS=lazy-graph-rag uv run python compare/run_matrix.py
```

Run the dataset ladder with a flavor selection:

```bash
uv run python scripts/run-dataset-ladder.py --flavors default,graph-rag-wide
```

`MATRIX_MODELS` and `MATRIX_FLAVORS` are intentionally mutually exclusive in the
dataset ladder runner: one is exact model selection, the other is manifest-driven
profile expansion.

## 6. Query-Time Versus Index-Time Knobs

The canonical shipped flavors are query-time only. Graph aliases select an Atlas
LightRAG profile with precedence `request overrides > profile > service default`;
they share one ingested graph and do not create profile-specific Neo4j schemas.
The rerank profile requires Atlas's `LIGHTRAG_RERANK_ADAPTER_ENABLED=true`, which
translates LightRAG's rerank request to the shared TEI service contract. None of
these profiles requires rebuilding Weaviate collections or the LightRAG graph.
Lazy graph flavors do not re-ingest
the source corpus, but a changed concept-density setting can rebuild their derived
cache from current Weaviate chunks. Each density uses an independent cache
namespace, so alternating fast, balanced, and wide flavors does not evict another
density.

Future index-time flavors should set `requires_reingest: true`. Examples:

- different chunk size or overlap;
- different embedding model;
- different contextual blurb prompt or document cap;
- different LightRAG extraction model or extraction concurrency.

The dataset ladder should cold-reset and re-ingest only when a selected flavor
requires index-time changes.

## 7. Reporting Effect

Matrix outputs now include:

```json
{
  "model": "graph-rag-wide",
  "base_model": "graph-rag",
  "flavor": "wide",
  "requires_reingest": false
}
```

Judgment files continue to score by `model`, so flavor aliases rank as separate
rows. This is deliberate: the question is not only which base approach wins, but
which tuned flavor wins as dataset complexity increases.
