# 2.5 Operations and Configuration

Use the [Quick Start](quickstart.md) for prerequisites and a first comparison.
This reference describes the current startup, request and configuration contracts.
Configure this consumer through its manifest; keep shared Atlas changes upstream.

## 1. Startup contract

`scripts/start-all.sh` selects the parent-owned `atlas.consumer.yml`, runs Atlas's native headless env
backfill, manifest-aware Compose validation, and consumer doctor, then starts Atlas
with `--no-tui --detach`.

The manifest sets durable `BASE_PORT: auto`, so Atlas
resolves a completely free 110-port block below the OS dynamic/private range once and
keeps it **stable across restarts** (persisted to `infra/.env`); set
`RAG_SHOWCASE_BASE_PORT` to pin a specific block instead (Atlas fails before startup
if it is occupied).

The run prints the live Open WebUI URL when it finishes, and every
port can be re-derived from `infra/.env`. It passes project name `rag-showcase`
(override with `RAG_SHOWCASE_PROJECT_NAME`). The manifest registers the project
identity, branding, `config/atlas.env.user`, external Compose overlay, backend plugin
root, Ollama model sidecar, and dataset-specific RAG ingestion profiles without
tracked Atlas modifications or a `_user` symlink.

Atlas applies the showcase project
and brand metadata (`rag-showcase-*` resources), waits on Compose health, and returns
before the script continues with the `gen-ai-rag` services (LightRAG, TEI reranker,
Weaviate, Neo4j, n8n, Open WebUI, and LiteLLM).

The manifest disables the
hardware-dependent Docling source; Atlas therefore falls through to its plain-text
parser and uses the profile's Chonkie recursive chunker.

Atlas derives dependency
enablement from service manifests, targets only enabled services, and returns its
detached health summary before the wrapper continues, assembles the corpus on the host
(`corpus/fetch_corpus.py`), waits for model readiness (embed + chat), submits the
`showcase_default` Atlas ingestion job, builds only the approach-specific contextual
index from Atlas-written chunks, and prints the Open WebUI URL. Atlas compiles the
consumer-declared LiteLLM aliases into `config.yaml` before the proxy boots, so they
are discoverable in `/v1/models` at startup with no consumer-side reconcile or proxy
restart.

On a fresh checkout, Atlas renders its initial bootstrap banner before
applying the consumer manifest, so that first banner can retain Atlas artwork;
subsequent starts use the configured RAG-SHOWCASE logo.

If Compose reports an exited-zero one-shot while other services are still starting,
the wrapper waits for runtime convergence only for that exact successful signature.
Missing, unhealthy or nonzero-exit services still fail. Local model downloads can
require several GB. Once startup prints the URL, follow [Quick Start](quickstart.md)
for the first comparison. Stop the selected stack with `./scripts/stop-all.sh`.

The explicitly selected experimental aliases are `lazy-graph-rag`,
`lazy-graph-rag-fast`, `lazy-graph-rag-balanced`, and `lazy-graph-rag-wide`.
They build an LLM-free concept graph from `RagBase` chunks.

`--include-flavor-tier`
runs two full matrix/judge passes: the base matrix expands from the canonical six
to all seven base approaches (adding `lazy-graph-rag`), and a second pass runs
all twelve flavor tuning aliases — the three `lazy-graph-rag` flavors above plus
the nine flavors of the other six approaches. The ad hoc default matrix (no flag)
remains the canonical six for backward compatibility.

The detached startup is the authoritative effective-config check: Atlas applies
the manifest's LightRAG container, TEI CPU and Docling-disabled configuration,
revalidates the resolved stack, and only then starts the enabled Compose services.
Compute sources are committed in `atlas.consumer.yml` (`profile: dev` plus
`env.values`: `LLM_PROVIDER_SOURCE: auto`, LightRAG container, TEI CPU, Docling
disabled), so the start passes no per-run source flags and is host-correct on every
machine. An alternate `ATLAS_CONSUMER_MANIFEST` can change models, branding, sources,
and other consumer values.

The `n8n-adaptive-rag` workflow is checked in at
[`n8n/adaptive-rag.workflow.json`](../../n8n/adaptive-rag.workflow.json) and declared in
`atlas.consumer.yml`. Atlas validates, namespaces, imports, activates, and probes the
workflow during startup — including activation with no `N8N_API_KEY`
([Atlas #720](https://github.com/thekaveh/atlas/issues/720)), so `start-all.sh`
performs no manual publish or n8n restart. See [`n8n/README.md`](../../n8n/README.md) for
the ownership, lifecycle, and tuning contract.

For the full corpus (MultiHop-RAG + keyword docs), `python3 -m pip install datasets`
on the host before running; without it, ingestion uses only the bundled keyword docs, so
the thematic / multi-hop demo queries have little to work with — see
[`corpus/README.md`](../../corpus/README.md).


## 2. Request and evaluation flow

Each approach is an OpenAI-compatible `/rag/<name>/v1/chat/completions` endpoint in a
self-contained plugin package (`backend_plugins/rag/`) that is bind-mounted into
Atlas's FastAPI backend through a generic "plugin seam". The seven base approaches
and twelve query-time flavors are declared in `atlas.consumer.yml`; Atlas validates
their ownership and routes, compiles them into LiteLLM's startup configuration,
and makes all nineteen aliases selectable in Open WebUI without admin-API
registration. Flavors such as `graph-rag-wide` route to the same base approach
with reproducible parameter overrides.

Open a multi-model chat, select the
approaches or flavors you want, and one prompt fans out with a uniform response
envelope, available evidence, and metrics.

The evaluation harness persists each cell
to append-safe JSONL, sends eligible evidence to Atlas's generic Ragas endpoint,
and keeps deterministic operational metrics separate from the optional blinded
judge panel.

The seven base approaches use the same embedding model and read the same corpus, so
the comparison is fair; LLM roles are **local-first** (see `backend_plugins/rag/roles.yaml`).
The lazy graph family remains excluded from default comparisons, but now has a
committed three-dataset quality and latency evaluation; see the
[experimental design and results](../../docs/lazy-graph-rag.md).


## 3. Repository layout

```
rag-showcase/
├── atlas.consumer.yml       # Atlas integration plus 19 aliases, workflows, and ingestion profiles
├── infra/                   # Atlas — vendored Git submodule (DO NOT edit here)
├── backend_plugins/rag/     # the plugin package mounted into Atlas's backend
│   ├── plugin.yml           # Atlas route, health, auth, env, and dependency contract
│   ├── common/              # shared routing, vector, LightRAG, flavor, and lazy-graph primitives
│   ├── approaches/          # seven routes, including experimental lazy graph
│   ├── tests/               # unit tests (mocked I/O)
│   ├── roles.yaml           # role→model map (local-first)
│   └── flavors.yaml         # Open WebUI/benchmark aliases with tuning overrides
├── ingest/                  # Atlas job client + contextual-index post-processor
├── corpus/                  # curated corpora + fetch/adapter scripts (MultiHop-RAG, keyword, graph-native, cyber-threat)
├── compose/                 # backend plugin compose overlay
├── config/                  # manifest-imported Atlas env values (LightRAG runtime defaults)
├── brand/                   # rag-showcase block-art logo (startup banner)
├── scripts/                 # start-all / stop-all / Atlas preflight / run-dataset-ladder
├── n8n/                     # Adaptive-RAG workflow recipe
├── demo/                    # contrasting query matrices (queries.yaml + per-dataset)
├── compare/                 # consumer evaluation manifest, resumable matrix, Ragas summaries, judges, reports
├── tests/                   # end-to-end integration harness (skips without the stack)
└── docs/                    # architecture, approaches, evaluation, comparison, results, specs & plans
```


## 4. Configuration

These environment variables configure the showcase at runtime. The plugin reads
most of them; the LightRAG role values are consumed by Atlas from the manifest's
`config/atlas.env.user`, while the Ollama sidecar is declared directly in
`atlas.consumer.yml`. Most are already injected by Atlas's backend or
by the showcase's compose overlay (`compose/rag-overlay.yml`); none need to be set
by hand for the default `start-all.sh` flow.

[`backend_plugins/rag/plugin.yml`](../../backend_plugins/rag/plugin.yml) is the
Atlas-validated source of truth for the plugin's `/rag` route root, health path,
auth policy, typed environment contract, and service dependencies. The table
below expands that operator contract with adjacent Atlas and startup settings.

| Variable | Default | Read by | Source |
|---|---|---|---|
| `LITELLM_BASE_URL` | `http://litellm:4000` | plugin LiteLLM client | Atlas backend env |
| `LITELLM_API_KEY` | — | plugin LiteLLM client, n8n workflow node | Atlas backend env |
| `BACKEND_INTERNAL_API_TOKEN` | — | Bearer used by LiteLLM aliases when invoking trusted backend plugin routes | Atlas `.env`; injected into LiteLLM by the consumer-model overlay |
| `LITELLM_MASTER_KEY` | — | External LiteLLM gateway authentication | Atlas `.env`; mapped to `LITELLM_API_KEY` in the backend |
| `WEAVIATE_URL` | `http://weaviate:8080` | vectors | Atlas backend env |
| `RAG_WEAVIATE_GRPC_PORT` | `50051` | vectors (in-network gRPC port; distinct from Atlas's host-published `WEAVIATE_GRPC_PORT`) | plugin manifest + overlay |
| `RAG_WEAVIATE_INIT_TIMEOUT_S` | `30` | vectors (Weaviate client init; covers transient gRPC readiness delay) | plugin manifest + overlay |
| `TEI_RERANKER_ENDPOINT` | `http://tei-reranker:80` | vectors (rerank) | overlay |
| `TEI_RERANKER_MAX_BATCH` | `32` | vectors (rerank request batch cap) | plugin manifest + overlay |
| `LIGHTRAG_ENDPOINT` | `http://lightrag:9621` | lightrag client | Atlas backend env |
| `LIGHTRAG_API_KEY` | — | lightrag client | Atlas backend env |
| `N8N_ADAPTIVE_WEBHOOK_URL` | `http://n8n:5678/webhook/adaptive-rag` | n8n approach | overlay |
| `LAZY_GRAPH_CACHE_DIR` | `/data/lazy-graph-rag` | lazy-graph-rag (persistent concept-graph cache, keyed by corpus digest) | plugin manifest + overlay |
| `RAG_ROLES_FILE` | `/app/plugins/rag/roles.yaml` | config | plugin manifest; supplied by `config/atlas.env.user` and overlay |
| `RAG_FLAVORS_FILE` | `/app/plugins/rag/flavors.yaml` | runtime flavor parameter loader | plugin manifest; supplied by `config/atlas.env.user` and overlay; aliases are declared in `atlas.consumer.yml` and drift-tested against this file |
| `RAG_INGESTION_PROFILE` | `showcase_default` | startup, Atlas ingestion job, collection selection | host env + overlay; dataset ladder sets the selected dataset id |
| `RAG_INGESTION_CORPUS_ROOT` | `/app/corpus` | Atlas ingestion job (container path the corpus mount resolves under) | overlay; pinned to match the `../corpus:/app/corpus:ro` mount instead of relying on Atlas's own default |
| `RAG_BASE_COLLECTION` | `RagBase_<profile>` | vanilla, hybrid, agentic vector tool, contextual post-step | derived by `start-all.sh`; override only with a matching Atlas profile target |
| `RAG_CONTEXTUAL_COLLECTION` | `RagContextual_<profile>` | contextual post-step and contextual-rag | derived by `start-all.sh` |
| `BACKEND_PLUGINS_DIR` | `/app/plugins` | plugin seam (Atlas) | overlay |
| `ATLAS_CONSUMER_MANIFEST` | `atlas.consumer.yml` | Atlas bootstrapper | host env; absolute path to the parent-owned consumer manifest |
| `LITELLM_DEFAULT_MODEL` | `ollama/qwen3.8:latest` | Atlas/LiteLLM chat fallback | `atlas.consumer.yml`; catalog alias, independent of host accelerator |
| `LITELLM_VISION_MODEL` | `ollama/qwen3.8:latest` | Atlas/LiteLLM vision fallback | `atlas.consumer.yml`; Qwen3.8 is multimodal |
| `OLLAMA_USER_MODELS` | `qwen3.8:latest,nomic-embed-text` | Atlas Ollama activation | `atlas.consumer.yml`; replaces stale generated model selections on upgrade |
| `LIGHTRAG_EXTRACT_LLM_MODEL` | `qwen3.8:latest` | LightRAG EXTRACT role | `config/atlas.env.user`; Atlas applies model-scoped `think:false` |
| `LIGHTRAG_KEYWORD_LLM_MODEL` | `qwen3.8:latest` | LightRAG KEYWORD role | `config/atlas.env.user`; Atlas applies model-scoped `think:false` |
| `LIGHTRAG_QUERY_LLM_MODEL` | `qwen3.8:latest` | LightRAG QUERY role | `config/atlas.env.user`; Atlas applies model-scoped `think:false` |
| `LIGHTRAG_EXTRACT_LLM_BINDING` | `openai` | LightRAG EXTRACT role provider | `config/atlas.env.user`; kept behind LiteLLM so Qwen3.8's catalog `think:false` default applies during ingestion |
| `LIGHTRAG_EXTRACT_LLM_BINDING_HOST` | `http://litellm:4000/v1` | LightRAG EXTRACT role endpoint | `config/atlas.env.user` |
| `LIGHTRAG_KEYWORD_LLM_BINDING` | `openai` | LightRAG KEYWORD role provider | `config/atlas.env.user`; same model-default path as EXTRACT |
| `LIGHTRAG_KEYWORD_LLM_BINDING_HOST` | `http://litellm:4000/v1` | LightRAG KEYWORD role endpoint | `config/atlas.env.user` |
| `LIGHTRAG_QUERY_LLM_BINDING` | `openai` | LightRAG QUERY role provider | `config/atlas.env.user`; same LiteLLM-passthrough reasoning as the KEYWORD role |
| `LIGHTRAG_QUERY_LLM_BINDING_HOST` | `http://litellm:4000/v1` | LightRAG QUERY role endpoint | `config/atlas.env.user` |
| `LIGHTRAG_EMBEDDING_MODEL` | `nomic-embed-text` | LightRAG embedding model | `config/atlas.env.user` |
| `LIGHTRAG_EXTRACT_MAX_ASYNC_LLM` | `1` | LightRAG EXTRACT concurrency | `config/atlas.env.user` |
| `LIGHTRAG_EXTRACT_LLM_TIMEOUT` | `900` | LightRAG EXTRACT timeout seconds | `config/atlas.env.user` |
| `LIGHTRAG_RERANK_ADAPTER_ENABLED` | `true` | LightRAG-to-TEI rerank adapter | `config/atlas.env.user`; see Troubleshooting below |
| `RAGAS_EVALUATOR_MODEL` | `qwen3.8:latest` | Ragas evaluator role | `config/atlas.env.user`; see [Evaluation Methodology](../../docs/evaluation-methodology.md) |
| `RAGAS_EMBEDDINGS_MODEL` | `nomic-embed-text` | Ragas embeddings role | `config/atlas.env.user`; see [Evaluation Methodology](../../docs/evaluation-methodology.md) |
| `LIGHTRAG_QUERY_ENABLE_RERANK` | `false` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_TOP_K` | `10` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_CHUNK_TOP_K` | `5` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_MAX_TOTAL_TOKENS` | `12000` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_PROFILES_FILE` | — (required) | lightrag client (`_load_profiles()`; graph-rag and agentic-rag always resolve a named profile) | plugin manifest; auto-generated and bind-mounted by Atlas's consumer LightRAG query profile overlay (#414) |
| `LIGHTRAG_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG base Ollama context cap (used only when a LightRAG role is bound directly to Ollama) | overlay |
| `LIGHTRAG_EXTRACT_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG EXTRACT-role Ollama context cap | overlay |
| `LIGHTRAG_KEYWORD_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG KEYWORD-role Ollama context cap | overlay |
| `LIGHTRAG_QUERY_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG QUERY-role Ollama context cap | overlay |
| `RAG_SHOWCASE_SKIP_DEFAULT_INGEST` | `0` | `start-all.sh` (skips corpus assembly + the default Atlas ingestion job; the dataset ladder sets it automatically) | host env |
| `RAG_SHOWCASE_PROJECT_NAME` | `rag-showcase` | `start-all.sh`, `stop-all.sh`, `eval_preflight.py --project` (Atlas Compose project identity) | host env |
| `RAG_SHOWCASE_BASE_PORT` | Atlas-resolved `BASE_PORT: auto` block | `start-all.sh` (pins a specific port block instead of the auto-resolved one) | host env |


## 5. Troubleshooting

- **First run looks stuck.** If you use Atlas's containerized Ollama source, it may
  be downloading several GB of local models; `start-all.sh` gates on model
  readiness, so let it finish. Watch progress: `docker logs -f "$(grep -E '^PROJECT_NAME=' infra/.env | tail -1 | cut -d= -f2-)-ollama-pull"`.
- **A model column never answers.** Confirm the Atlas-declared aliases are visible (`GET /v1/models`,
  or the LiteLLM model list). `n8n-adaptive-rag` additionally needs the Atlas-owned
  `atlas-consumer-adaptive-rag` workflow active. Re-run `./scripts/start-all.sh`;
  Atlas owns activation, including the no-API-key fallback, and the wrapper
  verifies the real production webhook. Do not manually import a second copy. See
  [`n8n/README.md`](../../n8n/README.md).
- **`contextual-rag` doesn't visibly win** on the context-starved query: that contrast needs
  Docling structure-aware chunking. The consumer manifest explicitly disables Docling for a
  hardware-neutral default, so Atlas uses plain-text parsing plus the profile's recursive
  chunker; select an Atlas-supported Docling source to preserve document structure.
- **Stack fails to come up with a Supabase / Postgres auth error** — e.g. `lightrag-init` exits
  with `password authentication failed for user "supabase_admin"`. This is an **Atlas stack**
  matter (the Supabase DB role/secret wiring), *not* the showcase. Back up data and verify the database credentials first. If you deliberately
  choose to erase this isolated stack, a cold reset re-initializes the database:
  `./scripts/stop-all.sh --cold` (this **wipes Atlas volumes/data**), then re-run
  `./scripts/start-all.sh`. See the [Atlas](https://github.com/thekaveh/atlas) repo.
- **Backend reports a module missing immediately after an `infra/` update.** Atlas
  currently recreates containers without rebuilding an existing local image. Run
  `cd infra && docker compose build backend`, return to the repo root, and rerun
  `./scripts/start-all.sh`. Automatic source-drift rebuilding is tracked in
  [Atlas #506](https://github.com/thekaveh/atlas/issues/506).
- **Local generation is too slow.** `LLM_PROVIDER_SOURCE: auto` already routes to a
  host Ollama when one is installed; to force a specific source, pass
  `--llm-provider-source` to `infra/start.sh` for one run (e.g. `ollama-localhost`
  for host Ollama, `ollama-container-gpu` for an NVIDIA-capable container runtime),
  or commit it in the manifest. LightRAG role models are now configured through Atlas's
  `LIGHTRAG_EXTRACT_LLM_MODEL`, `LIGHTRAG_KEYWORD_LLM_MODEL`, and
  `LIGHTRAG_QUERY_LLM_MODEL` inputs. Copy `atlas.consumer.yml` to the ignored
  `atlas.consumer.local.yml`, copy `config/atlas.env.user` to an ignored `.env.*`
  file, point the local manifest's `env.file` at that file, and set
  `ATLAS_CONSUMER_MANIFEST` to the local manifest for your model budget.
- **`graph-rag-rerank` fails while other graph profiles work.** Direct LightRAG
  rerank clients are not wire-compatible with TEI. Keep
  `LIGHTRAG_RERANK_ADAPTER_ENABLED=true` so Atlas translates and batches requests
  at TEI's 32-item limit. Canonical, fast, and wide remain rerank-disabled
  controls; their mode, fanout, and token budgets are Atlas query profiles.
- **A manual `cd infra && ./start.sh` follows logs.** For scripted Atlas bring-up,
  use `./start.sh --no-tui --detach` (or `--no-follow`) so Atlas waits for health,
  prints a status summary, and returns. `start-all.sh` already uses this path,
  then submits the Atlas-owned ingestion job and runs the showcase-only contextual
  enrichment step. See the
  [Atlas-reuse assessment](../../docs/atlas-reuse-assessment.md).
- **Integration tests skip.** `tests/test_demo_matrix.py` self-skips unless a live LiteLLM is
  reachable; with a started stack the gateway is derived from `infra/.env`
  automatically (see Quick Start development instructions for the non-default-gateway override).
- **Stop / reset:** `./scripts/stop-all.sh` to stop; `./scripts/stop-all.sh --cold` to stop **and**
  erase the selected project's Atlas volumes and data.
