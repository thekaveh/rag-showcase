# Quick Start

The whole showcase runs on [Atlas](https://github.com/thekaveh/atlas) (vendored as a
Git submodule at `infra/`) and comes up with **one command**.

## 1. Prerequisites

Atlas's requirements apply:

- **Docker** + **Docker Compose v2**, installed and running.
- The vendored `infra/` submodule initialized:
  ```bash
  git submodule update --init --recursive
  ```
- Host tools **`uv`** and **`python3`** (Atlas's bootstrapper and the host-side corpus fetch use them).
- An Atlas-supported LLM backend. The default local path uses Atlas's Ollama provider;
  set `LLM_PROVIDER_SOURCE=ollama-localhost` in `infra/.env` to use an existing host
  Ollama instead of the containerized one.
- Disk / RAM / headroom for the `gen-ai-rag` stack plus your chosen local models. The
  default local run activates `mistral-small3.2:24b` for LightRAG's graph roles — see
  [Hardware Sizing](../hardware.md) for minimum and recommended profiles.

## 2. Bring it up

```bash
./scripts/start-all.sh
```

This single script:

1. Runs the overlay setup (and **brands** the vendored Atlas as `rag-showcase` —
   `rag-showcase-*` containers/network and a startup banner).
2. Starts the Atlas `gen-ai-rag` stack — LightRAG, TEI reranker, Weaviate, Neo4j,
   Open WebUI, LiteLLM (Docling is off by default; ingestion falls back to naive
   text chunking) — plus n8n via an explicit `--n8n-source container` flag.
3. Waits for the backend, LightRAG, and Weaviate, then **assembles the corpus** on the
   host (`corpus/fetch_corpus.py`).
4. Waits for model readiness (embed + chat), **ingests** the corpus into the backend,
   and **registers** the canonical models plus any configured flavor aliases.
5. Prints the Open WebUI URL.

!!! tip "First run downloads models"
    With local models, the first run may pull several GB, so it takes a while.
    `start-all.sh` gates on model readiness — let it finish.

Then open the printed URL, start a **multi-model chat**, and select:
`vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`,
`n8n-adaptive-rag`. One prompt fans out to all of them.

Stop everything with:

```bash
./scripts/stop-all.sh
```

## 3. Corpus note

For the full corpus (MultiHop-RAG + keyword docs), install the `datasets` library on
the host before running:

```bash
python3 -m pip install datasets
```

Without it, ingestion uses only the bundled keyword docs, so the thematic / multi-hop
demo queries have little to work with. See the [Corpus Overview](../components/corpus.md).

## 4. The n8n workflow

The `n8n-adaptive-rag` workflow is checked in and imported automatically by
`start-all.sh`, which preserves its active state and restarts n8n so the production
webhook is registered. See the [n8n Adaptive Workflow](../components/n8n.md) page for
the workflow shape and tuning knobs.

## 5. Development and testing

```bash
uv run pytest                 # unit suite (mocked I/O) + integration tests (skip without the stack)
uv run pytest backend_plugins # unit tests only
```

The unit tests mock all external I/O and run without the stack. The
`tests/test_demo_matrix.py` integration tests exercise the live stack and self-skip
when LiteLLM is unreachable. They default to `http://localhost:4000`, which is not
where the stack publishes LiteLLM, so to run them from the host against a running
stack, point them at the published port and master key:

```bash
LITELLM_BASE_URL="http://localhost:$(grep -E '^LITELLM_PORT=' infra/.env | tail -1 | cut -d= -f2)" \
  LITELLM_MASTER_KEY="$(grep -E '^LITELLM_MASTER_KEY=' infra/.env | tail -1 | cut -d= -f2)" \
  uv run pytest tests
```

Build these docs locally with:

```bash
uv run --group docs mkdocs serve
```

Full environment-variable reference and troubleshooting live in the project
[README](https://github.com/thekaveh/rag-showcase#readme).
