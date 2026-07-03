# Overview

RAG Showcase compares six modern retrieval-augmented-generation (RAG) strategies
under **identical conditions** — same corpus, same embedding model, same generation
model — so the only variable is the *retrieval-and-reasoning strategy* itself. That
makes the comparison fair and the differences attributable.

## 1. How it runs

Each approach is an OpenAI-compatible `/<name>/v1/chat/completions` endpoint in a
self-contained plugin package (`backend_plugins/rag/`) that is **bind-mounted** into
Atlas's FastAPI backend through a generic *plugin seam*. Each endpoint is registered
into Atlas's **LiteLLM** gateway via its `/model/new` admin API, so the six approaches
appear automatically as selectable models in **Open WebUI**.

```mermaid
flowchart LR
    U[Open WebUI<br/>multi-model chat] -->|/v1/chat/completions| L[LiteLLM gateway]
    L --> R[RAG plugin seam<br/>backend_plugins/rag]
    R --> V[vanilla-rag]
    R --> H[hybrid-rag]
    R --> C[contextual-rag]
    R --> G[graph-rag]
    R --> A[agentic-rag]
    R --> N[n8n-adaptive-rag]
    V & H & C --> W[(Weaviate<br/>+ TEI rerank)]
    G & A --> LR[(LightRAG<br/>knowledge graph)]
    N --> WF[n8n workflow<br/>classify → route]
```

Open a multi-model chat, select the approaches (or flavors) you want, and one prompt
fans out — every answer comes back with a uniform **answer**, **retrieved-context**,
and **metrics** footer so they are directly comparable.

## 2. Flavors

Named tuning **flavors** such as `graph-rag-wide` or `hybrid-rag-high-recall` can also
appear as model aliases. They route to the same base approach with **reproducible
parameter overrides** (retrieval depth, rerank on/off, graph query mode, agent step
budget, …). One base approach can therefore be benchmarked at several operating points
without code changes. See [Flavor Tuning](../approach-flavor-tuning.md).

## 3. Fair-comparison guarantees

- **One corpus, ingested once** into both a plain vector collection (`RagBase`) and a
  context-prefixed collection (`RagContextual`), plus a LightRAG knowledge graph.
- **Shared models** — all approaches generate through the same LiteLLM model and embed
  with the same embedding model; LLM roles are **local-first** (`backend_plugins/rag/roles.yaml`).
- **Uniform output contract** — every approach returns the same answer/context/metrics
  shape, which the [evaluation harness](../evaluation-methodology.md) parses and scores.

## 4. Further reading

- [Quick Start](quickstart.md) — bring the whole stack up with one command.
- [Approach Internals](../approaches.md) — the exact steps, dependencies, and knobs per approach.
- [System Architecture](../architecture.md) — the full topology and per-approach flow phases.
- [Evaluation & Results](../evaluation-methodology.md) — how the judge panel and dataset ladder work.
