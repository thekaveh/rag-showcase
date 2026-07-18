# Per-Approach Service-Aware Data-Flow Diagrams Design

**Date:** 2026-07-17  
**Status:** Approved design, implementation pending  
**Audience:** rag-showcase maintainers, evaluators, and readers comparing RAG architectures

## 1. Objective

Add one comprehensive, landscape, service-aware data-flow diagram for every
currently implemented approach:

1. `vanilla-rag`
2. `hybrid-rag`
3. `contextual-rag`
4. `graph-rag`
5. `agentic-rag`
6. `n8n-adaptive-rag`
7. experimental `lazy-graph-rag`

Each diagram must explain what the approach does without requiring the reader to
infer service boundaries or message order from source code. The same canonical
documentation must publish correctly on all three supported surfaces:

- repository Markdown rendered by GitHub;
- the generated MkDocs `.io` site;
- the generated GitHub Wiki.

## 2. Chosen Design

Use one combined architecture-and-data-flow diagram per approach rather than a
separate architecture image and sequence image. Each diagram combines:

- deployment and ownership boundaries;
- concrete services and persistent stores;
- ingestion-time and query-time lanes where both exist;
- numbered messages and their important payload fields;
- retrieval, reranking, augmentation, generation, and response ordering;
- persistent state versus request-local state;
- tuning points and optional branches;
- the evidence and metadata returned to the caller.

This retains the existing full-system architecture and seven-lane comparison as
overview diagrams. The new diagrams are the detailed drill-down layer. Producing
fourteen separate images would duplicate most boxes and force readers to reconcile
two artifacts for every approach without adding equivalent explanatory value.

## 3. Canonical File Layout

Diagram sources and rendered images live together in approach-specific folders:

```text
docs/diagrams/approaches/
├── vanilla-rag/
│   ├── data-flow.html
│   └── data-flow.png
├── hybrid-rag/
│   ├── data-flow.html
│   └── data-flow.png
├── contextual-rag/
│   ├── data-flow.html
│   └── data-flow.png
├── graph-rag/
│   ├── data-flow.html
│   └── data-flow.png
├── agentic-rag/
│   ├── data-flow.html
│   └── data-flow.png
├── n8n-adaptive-rag/
│   ├── data-flow.html
│   └── data-flow.png
└── lazy-graph-rag/
    ├── data-flow.html
    └── data-flow.png
```

The HTML files are the editable architecture-diagram sources. They are standalone
documents with inline SVG and CSS. The PNG files are committed renderings for
GitHub Markdown, generated documentation, and offline viewing.

## 4. Shared Visual Contract

All seven diagrams use the architecture-diagram skill's dark technical design
system and the same semantic grammar:

| Visual element | Meaning |
|---|---|
| Cyan | User-facing client or OpenAI-compatible ingress |
| Emerald | Backend, orchestration, or approach logic |
| Violet | Persistent data, index, graph, cache, or collection |
| Amber | Model runtime or external compute dependency |
| Orange | Workflow/message routing or asynchronous handoff |
| Rose dashed line | Authentication or protected internal call |
| Solid numbered arrow | Required message in normal execution |
| Dashed numbered arrow | Optional, conditional, or cache-miss path |

Every diagram must meet these layout constraints:

- landscape SVG viewBox, approximately `1800 x 1000`;
- high-resolution PNG, approximately `3600 x 2000`;
- JetBrains Mono with a local monospace fallback;
- arrows drawn before opaque-backed component boxes;
- orthogonal routing with dedicated connection corridors;
- no line crossing through text or unrelated boxes;
- no overlapping boxes, labels, legends, or arrow markers;
- no dangling arrow heads or tails;
- legends outside service or deployment boundaries;
- stable component dimensions so labels do not shift the layout;
- a footer naming the invocation boundary and deployment location of the approach.

The main diagram body uses numbered messages. A compact message ledger beneath it
expands each number into the operation, representative payload, and response. This
keeps arrows readable while preserving protocol detail.

## 5. Per-Approach Content

### 5.1 Vanilla RAG

The diagram shows:

- Atlas ingestion job parsing and chunking the selected corpus;
- embedding chunks through LiteLLM/model routing;
- storage in profile-scoped `RagBase_<profile>` Weaviate collections;
- `POST /v1/chat/completions` with `model=vanilla-rag` entering LiteLLM;
- alias routing to the mounted rag-showcase backend plugin;
- query embedding, dense `nearVector` top-k retrieval, context stuffing, and one
  `light_gen` call;
- the OpenAI-compatible response plus exact `rag_showcase.sources` and metrics.

The tuning callout covers `k`, chunk profile, embedding role, and generation role.

### 5.2 Hybrid RAG

The diagram shows the shared base ingestion path and the query sequence:

- one query embedding;
- Weaviate BM25 plus dense hybrid retrieval using relative-score fusion and
  configurable `alpha`;
- `retrieve_k` candidates sent to the Atlas TEI reranker;
- `top_n` reranked chunks stuffed into the generation prompt;
- one `light_gen` call and structured sources/metrics returned.

The optional no-rerank flavor is a dashed bypass around TEI. The tuning callout
covers `retrieve_k`, `top_n`, `alpha`, and `rerank`.

### 5.3 Contextual RAG

The diagram has explicit ingestion and query lanes. Ingestion shows:

- Atlas's base parse/chunk output;
- the showcase contextualization post-step;
- one `contextual_blurb` model request per chunk;
- context prefix plus original chunk construction;
- embedding and persistence in `RagContextual_<profile>`.

The query lane shows hybrid retrieval, TEI reranking, context stuffing, shared
generation, and structured evidence. The diagram makes clear that enrichment is
performed once during ingestion, not on every query.

### 5.4 Graph RAG / LightRAG

The ingestion lane shows:

- Atlas RAG ingestion submitting full documents to LightRAG;
- EXTRACT-role entity and relationship extraction;
- graph, vector, document-status, and cache persistence through the Atlas-managed
  LightRAG storage services, including Neo4j;
- one shared graph per ingested corpus state, reused by all query profiles.

The query lane shows:

- `graph-rag` or flavor alias resolution in LiteLLM and the backend plugin;
- the selected Atlas LightRAG query profile;
- KEYWORD and QUERY model calls;
- LightRAG's graph/vector retrieval rather than a showcase-authored fixed k-hop
  Cypher query;
- optional LightRAG-to-TEI reranking through the Atlas adapter;
- answer-only evidence and query-profile metadata returned to the showcase.

The tuning callout covers mode, `top_k`, `chunk_top_k`, token budget, reranking,
and role-specific models. The diagram explicitly distinguishes Neo4j graph state
from the profile that controls query behavior.

### 5.5 Agentic RAG

The diagram shows a bounded, request-local ReAct loop:

- controller call through the `agentic` LiteLLM role;
- tool selection between `search_vectors(query)` and `query_graph(query)`;
- vector-tool path through embedding and Weaviate hybrid search;
- graph-tool path through LightRAG;
- tool observations appended to the current request's message history;
- repeated controller turns until a final answer or `max_steps` exhaustion;
- agent trace returned as evidence.

The diagram states that observations are not persisted or learned between
queries. The tuning callout covers `max_steps`, `vector_top_k`, `graph_mode`, tool
descriptions, system prompt, and controller model.

### 5.6 n8n Adaptive RAG

The diagram shows:

- OpenAI-compatible request routed to the thin backend wrapper;
- internal `POST {query}` to the Atlas-seeded n8n production webhook;
- classifier request through LiteLLM;
- `simple` versus `complex` routing decision;
- delegated backend call to `vanilla-rag` or `agentic-rag`;
- preservation of delegated `rag_showcase` evidence;
- response shaping with separate `adaptive: {route, approach}` metadata;
- return through the wrapper to LiteLLM and the caller.

The diagram labels the classifier and downstream timeout budgets and makes clear
that n8n is a routing policy, not an independent retriever.

### 5.7 Experimental Lazy Graph RAG

The diagram has a shared ingestion lane and a conditional query-time index lane:

- Atlas populates `RagBase_<profile>` in Weaviate;
- query embedding and concurrent hybrid seed retrieval plus full chunk read;
- named-volume cache lookup keyed by collection, corpus fingerprint, and concept
  density;
- cache-miss-only deterministic concept/co-occurrence graph construction with no
  LLM calls;
- relevance-budgeted graph expansion from seed chunks;
- selected chunks passed to the shared `light_gen` role;
- exact sources plus cache/index/traversal metadata returned.

The diagram explicitly states that this path does not use LightRAG or Neo4j. The
tuning callout covers seed count, relevance budget, context cap, and concepts per
chunk.

## 6. Documentation Integration

[`docs/approaches.md`](../../approaches.md) remains the canonical narrative. Each
approach section receives a `Service-Aware Data Flow` subsection immediately after
its purpose/intro and before the detailed internal-step list. The subsection:

1. embeds the approach PNG;
2. links to the standalone HTML source for full-size inspection;
3. states what its solid and dashed paths mean;
4. points readers to the section's step and tuning tables.

[`docs/architecture.md`](../../architecture.md) adds a drill-down index linking all
seven diagrams and explains how they relate to the system and parallel-lane
overviews. The README's architecture index is updated to say seven approaches and
to point readers to the per-approach drill-down section without embedding all
seven large images in the repository front page.

No separate Wiki-authored or site-authored prose is permitted. The existing
three-surface generator derives both from the canonical Markdown.

## 7. Three-Surface Asset Publication

The current docs builder handles only flat `docs/diagrams/*.html` files and the
two legacy `docs/diagrams/img/*.png` images. It must be extended to publish the
new nested approach assets recursively while preserving their relative paths:

| Canonical source | MkDocs generated target | Wiki generated target |
|---|---|---|
| `docs/diagrams/approaches/<id>/data-flow.png` | `generated/site/assets/diagrams/approaches/<id>/data-flow.png` | `generated/wiki/diagrams/approaches/<id>/data-flow.png` |
| `docs/diagrams/approaches/<id>/data-flow.html` | `generated/site/assets/diagrams/approaches/<id>/data-flow.html` | `generated/wiki/diagrams/approaches/<id>/data-flow.html` |

Markdown link rewriting must recognize the nested canonical paths and generate a
valid relative target for each output page. Existing flat architecture and
parallel-flow diagram behavior remains unchanged.

## 8. Verification Strategy

### 8.1 Contract Tests

Tests must verify:

- all seven expected approach directories exist;
- every directory has one `data-flow.html` and one `data-flow.png`;
- every HTML file contains one landscape inline SVG and the approach identifier;
- every corresponding section in `docs/approaches.md` embeds its unique PNG and
  links its unique HTML source;
- site and Wiki generation copy all fourteen nested assets;
- rewritten links in both generated surfaces resolve locally;
- existing flat diagrams remain published;
- the README and diagram index consistently say seven approaches.

### 8.2 Visual Inspection

Each HTML source is rendered with headless Chrome at 2x device scale. Every PNG is
inspected at original resolution for:

- clipped or unreadable text;
- overlapping boxes or labels;
- lines crossing component text;
- disconnected or dangling arrow markers;
- incorrect direction or numbering;
- legend placement inside a deployment boundary;
- excessive empty space or non-landscape framing.

Any failed image is corrected in the HTML source and regenerated. PNG-only manual
edits are prohibited.

### 8.3 Repository Verification

Before publication:

- run targeted diagram/docs contract tests;
- run `make docs-check` for deterministic three-surface generation and strict
  MkDocs build;
- run the full repository and backend-plugin test suites;
- run Ruff on changed Python files;
- run `git diff --check`;
- obtain an independent code/documentation review.

## 9. GitFlow Delivery

Work is isolated on `codex/per-approach-data-flow-diagrams`, branched from current
`develop` and pushed to origin before implementation. Completion uses:

1. feature branch pull request into `develop`;
2. required checks and merge;
3. `develop` pull request into `main`;
4. required checks and merge;
5. local/remote feature-branch cleanup;
6. verification that only `main` and `develop` remain and all worktrees are clean.

## 10. Acceptance Criteria

- Seven individual, detailed, landscape service-aware data-flow diagrams exist.
- Every diagram names the real services, stores, model roles, ordered messages,
  persistent state, response evidence, and relevant tuning points.
- Diagram statements match the current implementation and Atlas consumer
  declarations.
- No diagram contains overlapping content, dangling connectors, clipped text, or
  ambiguous arrow direction.
- Every approach section embeds its corresponding diagram.
- Repository Markdown, generated MkDocs site, and generated Wiki all contain the
  same explanatory material and working local diagram links.
- Existing overview diagrams remain available and accurately labeled.
- Documentation generation is deterministic and all required checks pass.
- Changes reach `develop` and then `main` through separate successful pull
  requests, followed by branch and worktree cleanup.

## 11. Non-Goals

- Changing approach behavior, model selection, or evaluation results.
- Creating a second implementation hierarchy for the seven approaches.
- Replacing the existing full-system architecture or comparative seven-lane flow.
- Hand-maintaining independent Wiki or site content.
- Adding diagrams for unimplemented candidates such as LLM Wiki or Graphify.
