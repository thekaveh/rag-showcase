# 2.2 Quick Start

The whole showcase runs on [Atlas](https://github.com/thekaveh/atlas) (vendored as a
Git submodule at `infra/`) and comes up with **one command**.

## 1. Prerequisites

Atlas's requirements apply:

- **Docker** + **Docker Compose 2.24.4 or newer**, installed and running. The
  temporary disabled-service compatibility overlay uses Compose's `!reset` tag.
- The vendored `infra/` submodule initialized:
  ```bash
  git submodule update --init --recursive
  ```
- Host tools **`uv`** and **`python3`** (Atlas's bootstrapper and the host-side corpus fetch use them).
- An Atlas-supported LLM backend. The default local path uses Atlas's Ollama provider;
  use an alternate parent-owned `ATLAS_ENV_USER_FILE` with
  `LLM_PROVIDER_SOURCE=ollama-localhost` to select an existing host Ollama.
- Disk / RAM / headroom for the `gen-ai-rag` stack plus your chosen local models. The
  default local run activates `mistral-small3.2:24b` for LightRAG's graph roles — see
  [Hardware Sizing](../hardware.md) for minimum and recommended profiles.

## 2. Bring It Up

```bash
./scripts/start-all.sh
```

This single script:

1. Selects `config/atlas.env.user`, runs Atlas's headless env backfill and
   Compose validation against a temporary merged env, and links the showcase
   Compose overlay.
2. Starts the Atlas `gen-ai-rag` stack with `--no-tui --detach`; Atlas applies
   the `rag-showcase` project and brand metadata, waits on Compose health, and
   returns. On a fresh checkout, the initial bootstrap banner can retain Atlas
   artwork because Atlas renders it before applying the external overlay. The
   stack includes LightRAG, TEI reranker, Weaviate, Neo4j,
   n8n, Open WebUI, and LiteLLM. The showcase wrapper explicitly disables the
   hardware-dependent Docling source, so ingestion uses portable naive text chunking,
   and temporarily enables MinIO for [Atlas #503](https://github.com/thekaveh/atlas/issues/503).
3. Proceeds after Atlas's detached health summary, then **assembles the corpus**
   on the host (`corpus/fetch_corpus.py`). If Atlas reports the known
   [exited-zero one-shot race](https://github.com/thekaveh/atlas/issues/508), the
   wrapper proceeds only when that exact log signature is present and a strict,
   provider-aware Docker-state check confirms every long-lived service is ready
   and every expected init service exited zero.
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

To customize Atlas-owned values without editing the submodule, copy the committed
overlay to an ignored local file and select it explicitly:

```bash
cp config/atlas.env.user .env.rag-showcase
# Edit .env.rag-showcase, then:
ATLAS_ENV_USER_FILE="$PWD/.env.rag-showcase" ./scripts/start-all.sh
```

Atlas's detached startup revalidates after applying the wrapper's source flags.
Those flags deliberately fix LightRAG to a container, TEI to its CPU container,
Docling to disabled, and MinIO to a temporary compatibility container. Alternate
env overlays customize provider, model, branding, and other consumer values; use
Atlas directly with different source flags for a different service topology.

## 3. Corpus Note

For the full corpus (MultiHop-RAG + keyword docs), install the `datasets` library on
the host before running:

```bash
python3 -m pip install datasets
```

Without it, ingestion uses only the bundled keyword docs, so the thematic / multi-hop
demo queries have little to work with. See the [Corpus Overview](../components/corpus.md).

## 4. The n8n Workflow

The `n8n-adaptive-rag` workflow is checked in and imported automatically by
`start-all.sh`, which preserves its active state and restarts n8n so the production
webhook is registered. See the [n8n Adaptive Workflow](../components/n8n.md) page for
the workflow shape and tuning knobs.

## 5. Development and Testing

```bash
uv run pytest                 # unit suite (mocked I/O) + integration tests (skip without the stack)
uv run pytest backend_plugins # unit tests only
```

The unit tests mock all external I/O and run without the stack. The
`tests/test_demo_matrix.py` integration tests exercise the live stack and self-skip
when LiteLLM is unreachable. With a started stack they derive the published gateway
and master key from `infra/.env` automatically, so a plain `uv run pytest tests`
works; export `LITELLM_BASE_URL` / `LITELLM_MASTER_KEY` only to target a
non-default gateway:

```bash
LITELLM_BASE_URL="http://other-host:4000" LITELLM_MASTER_KEY="sk-yourkey" \
  uv run pytest tests
```

Build these docs locally with:

```bash
uv run --group docs mkdocs serve
```

Full environment-variable reference and troubleshooting live in the project
[README](../../README.md).
