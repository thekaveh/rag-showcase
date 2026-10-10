# 2.2 Quick Start

The whole showcase runs on [Atlas](https://github.com/thekaveh/atlas) (vendored as a
Git submodule at `infra/`) and comes up with **one command**.

## 1. Prerequisites

Local shell commands require Git, Bash and Make. Install Python 3.10+ and `uv`.
Run commands from the checkout root, after checking the hardware requirements.

Atlas's requirements apply:

- **Docker** + **Docker Compose 2.20.3 or newer** (Atlas recommends 2.26.0+),
  installed and running. The Compose top-level file merges fragments via the
  native `include:` directive.
- Host tools **`uv`** and **`python3`** (Atlas's bootstrapper and the host-side corpus fetch use them).
- An Atlas-supported LLM backend. The manifest commits `LLM_PROVIDER_SOURCE: auto`,
  so each host resolves the best source (an existing host Ollama if installed, else
  a container) automatically — no per-run flag.
- Disk / RAM / headroom for the `gen-ai-rag` stack plus your chosen local models. The
  default local run uses Atlas's `qwen3.8:latest` for chat and all three LightRAG
  LLM roles, with `nomic-embed-text` for embeddings — see
  [Hardware Sizing](../hardware.md) for minimum and recommended profiles.

## 2. Bring It Up

From a fresh checkout, before any startup or corpus command:

```bash
git clone https://github.com/thekaveh/rag-showcase.git
cd rag-showcase
git submodule update --init --recursive
```

By default the bundled keyword corpus supports the first query below. For the
full MultiHop corpus, install `datasets` in your isolated host Python environment
before starting; see the corpus note below. Check that this selected showcase
project will not disrupt shared Atlas resources.

```bash
./scripts/start-all.sh
```

The script starts Atlas, assembles/ingests the corpus, waits for model and service
readiness and prints an Open WebUI URL. Local model downloads can take time.
Graph extraction has known host/version limits; see
[Running Graph Approaches Locally](local-graph-runs.md) if ingestion stalls.

Open the printed URL and complete Open WebUI sign-in/setup if prompted. Start a
multi-model chat and select `vanilla-rag` and `hybrid-rag`. Ask:
`What does error code WIDGET-ERR-7741 mean and how do I reset it?`
Expect a response from each selected model, with available evidence where provided.
Compare responses; no winner is guaranteed. Add other model aliases only as your
resource budget allows. Lazy graph is experimental and off in the default matrix.

Stop this selected stack with `./scripts/stop-all.sh`. Cold teardown erases Atlas
volumes/data. Read [Operations](operations.md) before resets or source/model overrides.

To customize Atlas-owned values without editing the submodule, copy the committed
manifest and env file, point the manifest copy at the env copy, and select it:

```bash
cp atlas.consumer.yml atlas.consumer.local.yml
cp config/atlas.env.user .env.rag-showcase
# In atlas.consumer.local.yml set env.file: ./.env.rag-showcase, then edit both.
ATLAS_CONSUMER_MANIFEST="$PWD/atlas.consumer.local.yml" ./scripts/start-all.sh
```

Atlas's detached startup revalidates after applying the consumer manifest.
All compute sources are committed in `atlas.consumer.yml` (`profile: dev` +
`env.values`): `LLM_PROVIDER_SOURCE: auto` (host-adaptive), LightRAG in a container,
TEI on its CPU container, and Docling disabled. So a plain start resolves the selected
host configuration without requiring a per-run source flag:

```bash
./scripts/start-all.sh
```

To pin or change a source, edit the manifest, or pass `--llm-provider-source` (etc.)
directly to `infra/start.sh` for a one-off — an operator flag wins that run.

ComfyUI is not required by the `gen-ai-rag` track, so omit its override unless an
enabled Atlas service actually needs it.

## 3. Corpus Note

For the full corpus (MultiHop-RAG + keyword docs), install the `datasets` library on
the host before running:

```bash
python3 -m pip install datasets
```

Without it, ingestion uses only the bundled keyword docs, so the thematic / multi-hop
demo queries have little to work with. See [`corpus/README.md`](../../corpus/README.md).

The dataset ladder selects the matching manifest profile (`baseline_curated`,
`graph_native`, and so on) before the stack starts. Atlas owns discover, parse,
chunk, embed, base-vector write, LightRAG upload, drain, and phase status. The
showcase retains only contextual-blurb generation because that transform belongs to
the `contextual-rag` approach rather than generic infrastructure.

## 4. The n8n Workflow

The `n8n-adaptive-rag` workflow is checked in and declared in
`atlas.consumer.yml`. Atlas validates, namespaces, imports, activates, and probes it
— including activation with no `N8N_API_KEY` (Atlas #720), so the wrapper does no
manual publish or n8n restart; it only verifies the real production webhook before
reporting readiness. See [`n8n/README.md`](../../n8n/README.md) for
ownership, lifecycle, workflow shape, and tuning knobs.

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
LiteLLM aliases, Weaviate plus its ingested collections, LightRAG (health plus
knowledge-graph population), the TEI reranker, n8n, and the required Ollama models
(pulled, not just declared), and flags an Ollama client/server version skew —
**without** running any ingestion, approach, or the LLM judge, run the read-only
preflight against a started stack:

```bash
make eval-check        # Atlas `doctor` (static) + live read-only dependency probes
```

It exits non-zero if anything is missing or unreachable, so it is a cheap gate
before an expensive matrix run.

Build these docs locally with:

```bash
uv run --group docs mkdocs serve
```

Full environment-variable reference and troubleshooting are in
[Operations and Configuration](operations.md).
