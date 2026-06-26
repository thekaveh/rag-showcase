# RAG Showcase

Six modern RAG approaches compared side-by-side in OpenWebUI's multi-model chat,
all running on [Atlas](https://github.com/thekaveh/atlas) (vendored as a Git
submodule at `infra/`). The project doubles as a deliberate test-drive of Atlas
as reusable infrastructure — see the [Atlas-reuse assessment](docs/atlas-reuse-assessment.md).

## 1. Overview

Each approach is an OpenAI-compatible `/<name>/v1/chat/completions` endpoint in a
self-contained plugin package (`backend_plugins/rag/`) that is bind-mounted into
Atlas's FastAPI backend through a generic "plugin seam". Each is registered into
Atlas's LiteLLM gateway via its `/model/new` admin API, so the six approaches
appear automatically as selectable models in OpenWebUI. Open a multi-model chat,
select all six, and one prompt fans out to every approach with a uniform
answer + retrieved-context + metrics surface.

The six approaches embed via the same LiteLLM model and read the same corpus, so
the comparison is fair; LLM roles are **local-first** (see `backend_plugins/rag/roles.yaml`).

## 2. Quick Start

**Prerequisites.** This runs entirely on [Atlas](https://github.com/thekaveh/atlas), so Atlas's
requirements apply:

- **Docker** + **Docker Compose v2**, installed and running.
- The vendored **`infra/` submodule initialized**: `git submodule update --init --recursive`.
- Host tools **`uv`** and **`python3`** (Atlas's bootstrapper and the host-side corpus fetch use them).
- Disk/RAM headroom for the `gen-ai-rag` stack **plus local Ollama models** — the first run pulls several GB.

```bash
./scripts/start-all.sh
```

This runs the overlay setup, starts the Atlas `gen-ai-rag` stack (LightRAG, TEI
reranker, Weaviate, Neo4j, OpenWebUI, LiteLLM; Docling is off by default —
ingestion falls back to naive text chunking) plus n8n (added via an explicit
`--n8n-source container` flag), waits for the backend, LightRAG, and Weaviate,
assembles the corpus on the host (`corpus/fetch_corpus.py`), waits for local model
readiness (embed + chat), ingests it into the backend container, registers the six
models, and prints the OpenWebUI URL. **First run downloads several GB of local models**, so
it takes a while. Then open the printed URL, start a multi-model chat, and select:
`vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`,
`n8n-adaptive-rag`. Stop everything with `./scripts/stop-all.sh`.

The `n8n-adaptive-rag` column also requires building and activating its workflow
once in the n8n UI — see [`n8n/README.md`](n8n/README.md).

For the full corpus (MultiHop-RAG + keyword docs), `python3 -m pip install datasets`
on the host before running; without it, ingestion uses only the bundled keyword docs, so
the thematic / multi-hop demo queries have little to work with — see
[`corpus/README.md`](corpus/README.md).

## 3. The Six Approaches

| Model | Approach | Visibly wins on |
|-------|----------|-----------------|
| `vanilla-rag` | dense top-k → stuff → one call (baseline) | — (the control) |
| `hybrid-rag` | Weaviate hybrid (BM25+dense) → TEI rerank | exact keyword / ID queries |
| `contextual-rag` | Anthropic Contextual Retrieval over context-prefixed chunks | context-starved chunks (clearest under Docling chunking) |
| `graph-rag` | wraps Atlas's LightRAG (graph + vector) | thematic / whole-corpus questions |
| `agentic-rag` | ReAct loop over vector + graph tools | multi-hop / comparative questions |
| `n8n-adaptive-rag` | low-code Adaptive-RAG workflow (routes by complexity) | mixed simple+complex batches |

## 4. Repository Layout

```
rag-showcase/
├── infra/                   # Atlas — vendored Git submodule (DO NOT edit here)
├── backend_plugins/rag/     # the plugin package mounted into Atlas's backend
│   ├── common/              # config, litellm, vectors, openai_io, pipeline, contextual, lightrag
│   ├── approaches/          # vanilla, hybrid, contextual, graph, agentic, n8n
│   ├── tests/               # unit tests (mocked I/O)
│   └── roles.yaml           # role→model map (local-first)
├── ingest/                  # corpus → chunk (Docling optional) → Weaviate(base+contextual) + LightRAG
├── register/                # idempotent LiteLLM /model/new registration
├── corpus/                  # curated corpus (MultiHop-RAG + keyword docs)
├── compose/                 # backend plugin compose overlay
├── scripts/                 # start-all / stop-all / setup-overlay
├── n8n/                     # Adaptive-RAG workflow recipe
├── demo/                    # contrasting query matrix (queries.yaml)
├── tests/                   # end-to-end integration harness (skips without the stack)
└── docs/                    # design spec, plan, Atlas-reuse assessment
```

## 5. Configuration (environment variables)

The plugin reads these at runtime. Most are already injected by Atlas's backend
or by the showcase's compose overlay (`compose/rag-overlay.yml`); none need to be
set by hand for the default `start-all.sh` flow.

| Variable | Default | Read by | Source |
|----------|---------|---------|--------|
| `LITELLM_BASE_URL` | `http://litellm:4000` | litellm client, register | Atlas backend env |
| `LITELLM_API_KEY` | — | litellm client, register (fallback) | Atlas backend env |
| `LITELLM_MASTER_KEY` | `sk-noauth` (register fallback) | register; n8n UI node | Atlas `.env` (not auto-sourced; mapped to `LITELLM_API_KEY` in-container) |
| `WEAVIATE_URL` | `http://weaviate:8080` | vectors | Atlas backend env |
| `WEAVIATE_GRPC_PORT` | `50051` | vectors | optional override |
| `TEI_RERANKER_ENDPOINT` | `http://tei-reranker:80` | vectors (rerank) | overlay |
| `LIGHTRAG_ENDPOINT` | `http://lightrag:9621` | lightrag client | Atlas backend env |
| `LIGHTRAG_API_KEY` | — | lightrag client | Atlas backend env |
| `DOCLING_ENDPOINT` | `""` (unset → naive chunking) | ingest | Atlas backend env (set only when Docling is enabled) |
| `N8N_ADAPTIVE_WEBHOOK_URL` | `http://n8n:5678/webhook/adaptive-rag` | n8n approach | overlay |
| `RAG_ROLES_FILE` | `/app/plugins/rag/roles.yaml` | config | overlay |
| `BACKEND_PLUGINS_DIR` | `/app/plugins` | plugin seam (Atlas) | overlay |

## 6. Documentation Index

| Document | Status | What it covers |
|----------|--------|----------------|
| [Design spec](docs/superpowers/specs/2026-06-25-rag-showcase-design.md) | Historical | The approved design: six approaches, architecture, corpus, phasing (predates implementation — see its deviations note) |
| [Implementation plan](docs/superpowers/plans/2026-06-25-rag-showcase.md) | Historical | The task-by-task implementation plan (Tasks 0–19, as-built) |
| [Atlas-reuse assessment](docs/atlas-reuse-assessment.md) | Living | What reused cleanly, friction found, recommendations for Atlas |
| [Corpus](corpus/README.md) | Living | How to populate the corpus |
| [n8n workflow](n8n/README.md) | Living | Building the Adaptive-RAG workflow in the n8n UI |

## 7. Development & Testing

```bash
uv run pytest                 # unit suite (mocked I/O) + integration tests (skip without the stack)
uv run pytest backend_plugins # unit tests only
```

The unit tests mock all external I/O and run without the stack. The
`tests/test_demo_matrix.py` integration tests exercise the live stack and
self-skip when LiteLLM is unreachable. They default to `http://localhost:4000`,
which is not where the stack publishes LiteLLM (that's `LITELLM_PORT`), so to run
them from the host against a running stack, point them at the published port and
master key:

```bash
LITELLM_BASE_URL="http://localhost:$(grep -E '^LITELLM_PORT=' infra/.env | tail -1 | cut -d= -f2)" \
  LITELLM_MASTER_KEY="$(grep -E '^LITELLM_MASTER_KEY=' infra/.env | tail -1 | cut -d= -f2)" \
  uv run pytest tests
```

## 8. Troubleshooting

- **First run looks stuck.** It is downloading several GB of local Ollama models
  (`qwen3.6:latest`, `nomic-embed-text`, `qwen3-embedding:0.6b`); `start-all.sh` gates on model
  readiness, so let it finish. Watch progress: `docker logs -f "$(grep -E '^PROJECT_NAME=' infra/.env | tail -1 | cut -d= -f2)-ollama-pull"`.
- **A model column never answers.** Confirm all six registered (`docker logs <project>-backend`,
  or the LiteLLM model list). `n8n-adaptive-rag` additionally needs its workflow **built and
  activated** in the n8n UI — see [`n8n/README.md`](n8n/README.md).
- **`contextual-rag` doesn't visibly win** on the context-starved query: that contrast needs
  Docling structure-aware chunking, which is **off by default** (ingestion falls back to naive
  chunking). Enable Docling in the Atlas stack to see it.
- **Stack fails to come up with a Supabase / Postgres auth error** — e.g. `lightrag-init` exits
  with `password authentication failed for user "supabase_admin"`. This is an **Atlas stack**
  matter (the Supabase DB role/secret wiring), *not* the showcase. The reliable fix is a clean
  reset so the Atlas Supabase DB re-initializes against the current secrets:
  `cd infra && ./stop.sh --cold` (this **wipes Atlas volumes/data**), then re-run
  `./scripts/start-all.sh`. See the [Atlas](https://github.com/thekaveh/atlas) repo.
- **Integration tests skip.** `tests/test_demo_matrix.py` self-skips unless a live LiteLLM is
  reachable; point it at the published port + master key (see §7).
- **Stop / reset:** `./scripts/stop-all.sh` to stop; `cd infra && ./stop.sh --cold` to stop **and**
  wipe all Atlas data.
