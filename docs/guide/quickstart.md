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
- An Atlas-supported LLM backend. The wrapper leaves provider selection to Atlas;
  set `RAG_SHOWCASE_LLM_PROVIDER_SOURCE=ollama-localhost` for one run when an
  existing host Ollama should be used.
- Disk / RAM / headroom for the `gen-ai-rag` stack plus your chosen local models. The
  default local run activates `mistral-small3.2:24b` for LightRAG extraction and
  uses `qwen3.6:latest` for graph keyword/query roles — see
  [Hardware Sizing](../hardware.md) for minimum and recommended profiles.

## 2. Bring It Up

```bash
./scripts/start-all.sh
```

This single script:

1. Starts Atlas with `--base-port auto`, so Atlas selects a completely free 110-port
   block below the OS dynamic/private range and persists it to `infra/.env`.
   The project name is `rag-showcase`. Set `RAG_SHOWCASE_BASE_PORT` to pin a
   specific block; Atlas rejects it if any port is occupied.
2. Selects `atlas.consumer.yml` and runs Atlas's native headless env backfill,
   manifest-aware Compose validation, and consumer doctor. The manifest declares
   project/brand metadata, the env
   file, external Compose overlay, backend plugin root, nineteen LiteLLM aliases,
   Ollama sidecar, adaptive workflow, and RAG ingestion profiles without tracked
   Atlas modifications or a `_user` symlink.
3. Starts the Atlas `gen-ai-rag` stack with `--no-tui --detach`; Atlas applies
   the `rag-showcase` project and brand metadata, waits on Compose health, and
   returns. On a fresh checkout, the initial bootstrap banner can retain Atlas
   artwork because Atlas renders it before applying the consumer manifest. The
   stack includes LightRAG, TEI reranker, Weaviate, Neo4j,
   n8n, Open WebUI, and LiteLLM. The showcase wrapper explicitly disables the
   hardware-dependent Docling source, so Atlas falls back to plain-text parsing and
   the selected profile's Chonkie recursive chunker. Atlas starts only the enabled
   service set and owns dependency and initial one-shot classification.
4. Proceeds after Atlas's detached health summary, then **assembles the corpus**
   on the host (`corpus/fetch_corpus.py`). If Atlas reports the known
   [exited-zero one-shot race](https://github.com/thekaveh/atlas/issues/508), the
   wrapper proceeds only when that exact log signature is present and a strict,
   provider-aware Docker-state check confirms every long-lived service is ready
   and every expected init service exited zero.
5. Waits for model readiness (embed + chat), submits the `showcase_default` Atlas
   **RAG ingestion job**, waits on its machine-readable phase record, and then builds
   the contextual collection from Atlas-written plain chunks. It verifies all
   Atlas-declared base and flavor aliases. Each start also removes
   any exact legacy database duplicates from the retired registration script,
   including rows restored with an older database, without touching unrelated models.
   If cleanup occurs, LiteLLM reloads once so all four workers discard stale routes.
6. Prints the Open WebUI URL.

!!! tip "First run downloads models"
    With local models, the first run may pull several GB, so it takes a while.
    `start-all.sh` gates on model readiness — let it finish.

Then open the printed URL, start a **multi-model chat**, and select:
`vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`,
`n8n-adaptive-rag`, `lazy-graph-rag`. One prompt fans out to all of them.

Stop everything with:

```bash
./scripts/stop-all.sh
```

To customize Atlas-owned values without editing the submodule, copy the committed
manifest and env file, point the manifest copy at the env copy, and select it:

```bash
cp atlas.consumer.yml atlas.consumer.local.yml
cp config/atlas.env.user .env.rag-showcase
# In atlas.consumer.local.yml set env.file: ./.env.rag-showcase, then edit both.
ATLAS_CONSUMER_MANIFEST="$PWD/atlas.consumer.local.yml" ./scripts/start-all.sh
```

Atlas's detached startup revalidates after applying the wrapper's source flags.
The stable service contracts deliberately fix LightRAG to a container, TEI to its
CPU container, and Docling to disabled. LLM and ComfyUI sources are not assumed:
the wrapper uses Atlas's active configuration unless
`RAG_SHOWCASE_LLM_PROVIDER_SOURCE` or `RAG_SHOWCASE_COMFYUI_SOURCE` is supplied.
Alternate consumer manifests customize model roles, branding, and other values.

For example, a host-runtime launch is explicit and leaves unrelated host services
under their existing owners:

```bash
RAG_SHOWCASE_LLM_PROVIDER_SOURCE=ollama-localhost \
RAG_SHOWCASE_COMFYUI_SOURCE=managed-localhost-mps \
./scripts/start-all.sh
```

ComfyUI is not required by the `gen-ai-rag` track, so omit its override unless an
enabled Atlas service actually needs it.

## 3. Corpus Note

For the full corpus (MultiHop-RAG + keyword docs), install the `datasets` library on
the host before running:

```bash
python3 -m pip install datasets
```

Without it, ingestion uses only the bundled keyword docs, so the thematic / multi-hop
demo queries have little to work with. See the [Corpus Overview](../components/corpus.md).

The dataset ladder selects the matching manifest profile (`baseline_curated`,
`graph_native`, and so on) before the stack starts. Atlas owns discover, parse,
chunk, embed, base-vector write, LightRAG upload, drain, and phase status. The
showcase retains only contextual-blurb generation because that transform belongs to
the `contextual-rag` approach rather than generic infrastructure.

## 4. The n8n Workflow

The `n8n-adaptive-rag` workflow is checked in and declared in
`atlas.consumer.yml`. Atlas validates, namespaces, imports, and probes it; the
wrapper verifies the real production webhook before reporting readiness. A narrow
publish/reload compatibility step remains for no-API-key installs until Atlas #514
lands. See the [n8n Adaptive Workflow](../components/n8n.md) page for ownership,
lifecycle, workflow shape, and tuning knobs.

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

To confirm the evaluation's Atlas-infra dependencies are up and in order — the
LiteLLM aliases, Weaviate plus its ingested collections, LightRAG, the TEI
reranker, and n8n — **without** running any ingestion, approach, or the LLM judge,
run the read-only preflight against a started stack:

```bash
make eval-check        # Atlas `doctor` (static) + live read-only dependency probes
```

It exits non-zero if anything is missing or unreachable, so it is a cheap gate
before an expensive matrix run.

Build these docs locally with:

```bash
uv run --group docs mkdocs serve
```

Full environment-variable reference and troubleshooting live in the project
[README](../../README.md).
