---
hide:
  - navigation
---

# 1 RAG Showcase

<div class="hero-tagline" markdown>
Six modern RAG approaches, compared side by side — each served as an OpenAI-compatible
endpoint on a fully-local [Atlas](https://github.com/thekaveh/atlas) stack. Ask one
question in Open WebUI and watch the approaches answer in parallel, with a uniform
answer, retrieved-context, and metrics surface. It doubles as a reproducible evaluation
harness that measures *which approach wins on which kind of question*.
</div>

[Quick Start](guide/quickstart.md){ .md-button .md-button--primary }
[Measured Results](comparison.md){ .md-button }

## 1. The Six Approaches

| Endpoint | Approach | Designed to shine on |
|----------|----------|----------------------|
| [`vanilla-rag`](approaches.md#3-vanilla-rag) | Dense top-k retrieval, then a single generation call (the control) | Simple factoids; the baseline |
| [`hybrid-rag`](approaches.md#4-hybrid-rag) | Weaviate hybrid retrieval (BM25 + dense), then TEI reranking | Exact keyword and identifier queries |
| [`contextual-rag`](approaches.md#5-contextual-rag) | Anthropic Contextual Retrieval over context-prefixed chunks | Context-starved chunks |
| [`graph-rag`](approaches.md#6-graph-rag) | LightRAG over extracted entities, relationships, and vector context | Graph-shaped relationship questions |
| [`agentic-rag`](approaches.md#7-agentic-rag) | ReAct loop over vector and graph retrieval tools | Multi-hop and comparative questions |
| [`n8n-adaptive-rag`](approaches.md#8-n8n-adaptive-rag) | Low-code workflow that routes by query complexity | Mixed simple-and-complex batches |

The last column is the design intent behind each demo query family, not a measured
result — the committed runs contradict some intended contrasts (see the
[per-query winners](dataset-complexity-report.md)).

Any approach can also expose tuned **flavors** — for example `hybrid-rag-high-recall`
or `graph-rag-fast` — that route to the same base approach with reproducible parameter
overrides and their own selectable model alias. See [Flavor Tuning](approach-flavor-tuning.md).

## 2. Headline Result

The 2026-07-03 ladder ran fourteen approach and flavor aliases across three datasets of
increasing structure. The winner shifts with input complexity, which is the point:

| Dataset | Winning configuration | Judge score |
|---------|-----------------------|:-----------:|
| Baseline curated | `vanilla-rag-wide` | 4.42 |
| Graph-native dossiers | `hybrid-rag-high-recall` | 4.25 |
| Cyber-threat graph (MITRE ATT&CK) | `contextual-rag-high-recall` | 3.58 |

Full per-query winners, judge methodology, and raw snapshots are in
[Evaluation and Results](evaluation-methodology.md).

## 3. Documentation

<div class="grid cards" markdown>

-   **Get Started**

    ---

    Prerequisites, one-command bring-up, and driving the comparison in Open WebUI.

    [Quick Start](guide/quickstart.md)

-   **The Approaches**

    ---

    Step-by-step internals, dependencies, and tuning knobs for each of the six.

    [Approach Internals](approaches.md)

-   **Evaluation and Results**

    ---

    Judge-panel methodology, the dataset complexity ladder, and the measured rankings.

    [Methodology](evaluation-methodology.md)

-   **Architecture**

    ---

    The plugin seam, LiteLLM, retrieval stores, and workflow services.

    [System Architecture](architecture.md)

</div>

## 4. Fully Local by Default

Everything runs on your own machine: local models through Atlas's Ollama provider
(`qwen3.6:latest` for chat, `nomic-embed-text` for embeddings, and `mistral-small3.2:24b`
for LightRAG's graph roles), Weaviate and LightRAG for retrieval, a TEI reranker, and a
local judge panel. No cloud calls are required to run the showcase or reproduce its
results. See the [Hardware Sizing](hardware.md) guide for minimum and recommended profiles.

The project is also a deliberate test-drive of Atlas as reusable infrastructure. The
[Atlas Reuse Assessment](atlas-reuse-assessment.md) records what reused cleanly, the
seams that were added, and the [pinned dependency contracts](dependency-contracts.md)
each integration was verified against.
