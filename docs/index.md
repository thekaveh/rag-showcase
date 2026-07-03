# RAG Showcase

**Six modern RAG strategies, compared side-by-side** — each served as an
OpenAI-compatible endpoint on a fully-local [Atlas](https://github.com/thekaveh/atlas)
stack. Open a multi-model chat in **Open WebUI**, ask one question, and watch the
approaches answer in parallel with a uniform **answer + retrieved-context + metrics**
surface.

It doubles as a reproducible **evaluation harness**: a query × approach matrix, a
local LLM **judge panel**, and a dataset **complexity ladder** that measures *which
approach wins on which kind of question*.

[Get running in one command](guide/quickstart.md){ .md-button .md-button--primary }
[See the measured results](comparison.md){ .md-button }

## The six approaches

| Endpoint | Strategy | Shines on |
|----------|----------|-----------|
| [`vanilla-rag`](approaches.md#3-vanilla-rag) | Dense top-k → stuff → one call (the control) | simple factoids / the baseline |
| [`hybrid-rag`](approaches.md#4-hybrid-rag) | Weaviate hybrid (BM25 + dense) → TEI rerank | exact keyword / identifier queries |
| [`contextual-rag`](approaches.md#5-contextual-rag) | Anthropic Contextual Retrieval over context-prefixed chunks | context-starved chunks |
| [`graph-rag`](approaches.md#6-graph-rag) | LightRAG over extracted entities, relationships + vector context | graph-shaped relationship questions |
| [`agentic-rag`](approaches.md#7-agentic-rag) | ReAct loop over vector + graph retrieval tools | multi-hop / comparative questions |
| [`n8n-adaptive-rag`](approaches.md#8-n8n-adaptive-rag) | Low-code workflow that routes by query complexity | mixed simple + complex batches |

Any approach can also expose tuned **flavors** (e.g. `hybrid-rag-high-recall`,
`graph-rag-fast`) — same base approach, reproducible parameter overrides, its own
selectable model alias. See [Flavor Tuning](approach-flavor-tuning.md).

!!! abstract "Headline result — 2026-07-03 ladder (14 aliases × 3 datasets)"
    Winners shift with input complexity, which is the whole point:

    - **Baseline curated** → `vanilla-rag-wide` (4.42) — wide dense retrieval is enough.
    - **Graph-native dossiers** → `hybrid-rag-high-recall` (4.25) — high-recall hybrid leads the aggregate.
    - **Cyber-threat graph (MITRE ATT&CK)** → `contextual-rag-high-recall` (3.58) — context-prefixing pulls ahead.

    Full per-query winners, judge methodology, and raw snapshots live under
    [Evaluation & Results](evaluation-methodology.md).

## Explore

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } **Get Started**

    ---

    Prerequisites, one-command bring-up, and how to drive the comparison in Open WebUI.

    [:octicons-arrow-right-24: Quick Start](guide/quickstart.md)

-   :material-sitemap:{ .lg .middle } **The Approaches**

    ---

    Step-by-step internals, dependencies, and tuning knobs for each of the six.

    [:octicons-arrow-right-24: Approach Internals](approaches.md)

-   :material-scale-balance:{ .lg .middle } **Evaluation & Results**

    ---

    The judge-panel methodology, the dataset complexity ladder, and the measured rankings.

    [:octicons-arrow-right-24: Methodology](evaluation-methodology.md)

-   :material-graph-outline:{ .lg .middle } **Architecture**

    ---

    How the plugin seam, LiteLLM, retrieval stores, and workflow services fit together.

    [:octicons-arrow-right-24: System Architecture](architecture.md)

</div>

## Fully local by default

Everything runs on your machine — local models via Atlas's Ollama provider
(`qwen3.6:latest` for chat, `nomic-embed-text` for embeddings, `mistral-small3.2:24b`
for LightRAG's graph roles), Weaviate + LightRAG for retrieval, a TEI reranker, and a
**local** judge panel. No cloud calls are required to run the showcase or reproduce
its results. See the [Hardware Sizing](hardware.md) guide for minimum and recommended
profiles.

The project is also a deliberate test-drive of Atlas as reusable infrastructure — the
[Atlas Reuse Assessment](atlas-reuse-assessment.md) records what reused cleanly, the
seams that were added, and the [pinned dependency contracts](dependency-contracts.md)
each integration was verified against.
