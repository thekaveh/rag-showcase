# Architecture and Flow Diagrams

This page documents the two generated landscape diagrams used by the README:
the project architecture map and the parallel flow map for all six RAG approaches.
Both diagrams are checked in as high-resolution PNGs and as standalone HTML/SVG
source files.

## 1. Detailed Project Architecture

![RAG Showcase detailed architecture](architecture-detailed.png)

Source: [`architecture-detailed.html`](architecture-detailed.html).
PNG: [`architecture-detailed.png`](architecture-detailed.png).

### 1.1 User and evaluation surface

OpenWebUI and the comparison harness both call the same LiteLLM gateway. OpenWebUI
is the interactive multi-model chat surface; `compare/run_matrix.py` is the repeatable
test runner; `compare/judge.py` scores stored answer matrices with local judge models.

### 1.2 Atlas backend and plugin seam

Atlas provides the reusable infrastructure. Rag-showcase adds a mounted FastAPI
plugin under `backend_plugins/rag`, where each approach exposes an OpenAI-compatible
`/<approach>/v1/chat/completions` endpoint. `register/register_models.py` registers
those endpoints into LiteLLM as selectable model names.

The six approach endpoints are deployed inside the Atlas backend container, not as
six separate containers. OpenWebUI and `compare/run_matrix.py` invoke them through
LiteLLM's `/v1/chat/completions` surface after LiteLLM maps the selected model name
to the corresponding backend route.

### 1.3 Retrieval stores and workflow services

The direct retrieval approaches use Weaviate collections (`RagBase` and
`RagContextual`), with TEI reranking for hybrid/contextual paths. `graph-rag` and
the graph tool inside `agentic-rag` delegate to LightRAG and Neo4j. `n8n-adaptive-rag`
bridges into the n8n workflow and reports the selected route.

### 1.4 Host model strategy

On macOS, Docker containers cannot use Apple Metal GPU acceleration. The architecture
therefore routes large local model calls to host Ollama at `host.docker.internal:11434`.
Generation uses the Qwen MoE model with `think:false`; LightRAG uses a non-reasoning
model for extraction/query; embeddings use `nomic-embed-text`.

## 2. Six Approach Flow Phases

![RAG Showcase six approach flow phases](approach-flows.png)

Source: [`approach-flows.html`](approach-flows.html).
PNG: [`approach-flows.png`](approach-flows.png).

### 2.1 Shared setup

All approaches start from the same corpus ingestion pipeline: load documents, chunk
them, embed chunks, build contextual chunks, upload source text to LightRAG, and
register the six approach endpoints into LiteLLM.

### 2.2 Direct retrieval lanes

`vanilla-rag`, `hybrid-rag`, and `contextual-rag` all finish with one generation call
over selected evidence. They differ mainly in how evidence is selected: dense top-k,
hybrid retrieval plus reranking, or contextualized chunks plus reranking.

### 2.3 Graph and agentic lanes

`graph-rag` delegates the whole answer to LightRAG hybrid mode over extracted entities,
relationships, and vector context. `agentic-rag` runs a bounded ReAct loop that can
call vector search or graph query tools before returning a final answer and tool trace.

### 2.4 Adaptive workflow lane

`n8n-adaptive-rag` is a workflow bridge. The n8n workflow classifies the query,
routes it to a selected approach, shapes the response, and returns the answer plus
route metadata to the OpenAI-compatible wrapper.

All six lanes are invoked the same way from the outside: the caller chooses a model
alias in LiteLLM, and LiteLLM forwards to the mounted FastAPI route in the Atlas
backend container.

## 3. Regeneration Notes

The diagrams are standalone HTML files with inline SVG. To regenerate the PNGs from
Chrome on macOS:

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=2000,1300 --force-device-scale-factor=2 \
  --screenshot=docs/architecture-detailed.png \
  file://"$PWD"/docs/architecture-detailed.html

"$CHROME" --headless=new --disable-gpu --hide-scrollbars \
  --window-size=2000,1300 --force-device-scale-factor=2 \
  --screenshot=docs/approach-flows.png \
  file://"$PWD"/docs/approach-flows.html
```
