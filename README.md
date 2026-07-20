# RAG Showcase

Seven RAG approaches compared side-by-side in Open WebUI's multi-model chat,
all running on [Atlas](https://github.com/thekaveh/atlas) (vendored as a Git
submodule at `infra/`). The project doubles as a deliberate test-drive of Atlas
as reusable infrastructure — see the [Atlas-reuse assessment](docs/atlas-reuse-assessment.md).

> **Live results (2026-07-17).** The current committed run evaluated seven base
> approaches and twelve named query-time flavors across baseline curated,
> graph-native, and MITRE ATT&CK cyber-threat datasets. All **380/380** answer
> cells succeeded: 140 base-family cells and 240 flavor cells. `vanilla-rag` led
> baseline, experimental `lazy-graph-rag` led graph-native, and `contextual-rag`
> led cyber by the blinded two-model judge panel. The flavor winners were
> `lazy-graph-rag-wide`, `hybrid-rag-high-recall`, and `hybrid-rag-fast`.
> Atlas Ragas returned coverage-aware faithfulness and answer-relevancy scores;
> LightRAG answer-only rows are correctly ineligible for faithfulness. These are
> concise headline winners; the complete
> **[`docs/evaluation-results.md`](docs/evaluation-results.md)** leaderboards contain
> every approach and metric. Read the [methodology](docs/evaluation-methodology.md),
> [dataset ladder](docs/dataset-complexity-report.md), [narrative comparison](docs/comparison.md),
> and [artifact ledger](docs/results/README.md) for their distinct supporting views.

## 1. Overview

Each approach is an OpenAI-compatible `/rag/<name>/v1/chat/completions` endpoint in a
self-contained plugin package (`backend_plugins/rag/`) that is bind-mounted into
Atlas's FastAPI backend through a generic "plugin seam". The seven base approaches
and twelve query-time flavors are declared in `atlas.consumer.yml`; Atlas validates
their ownership and routes, compiles them into LiteLLM's startup configuration, and makes all nineteen
aliases selectable in Open WebUI without admin-API registration.
Flavors such as `graph-rag-wide` route to the same base approach with reproducible
parameter overrides. Open a multi-model chat, select
the approaches or flavors you want, and one prompt fans out with a uniform answer,
retrieved-context, and metrics surface. The evaluation harness persists each cell
to append-safe JSONL, sends eligible evidence to Atlas's generic Ragas endpoint,
and keeps deterministic operational metrics separate from the optional blinded
judge panel.

The seven base approaches use the same embedding model and read the same corpus, so
the comparison is fair; LLM roles are **local-first** (see `backend_plugins/rag/roles.yaml`).
The lazy graph family remains excluded from default comparisons, but now has a
committed three-dataset quality and latency evaluation; see the
[experimental design and results](docs/lazy-graph-rag.md).

## 2. Architecture Diagrams

### 2.1 Detailed project architecture

![RAG Showcase detailed architecture](docs/diagrams/img/architecture-detailed.png)

*Atlas stack, LiteLLM gateway, mounted backend plugin seam, seven RAG endpoints,
retrieval stores, workflow services, and Atlas-managed model routing. Source:
[`docs/diagrams/architecture-detailed.html`](docs/diagrams/architecture-detailed.html). Full explanation:
[`docs/architecture.md`](docs/architecture.md).*

The seven RAG approaches are mounted FastAPI routes inside the Atlas backend container;
Atlas declares each route as a LiteLLM model alias, and Open WebUI or the comparison harness
invoke them through LiteLLM's OpenAI-compatible `/v1/chat/completions` surface.

### 2.2 Seven approach flow phases

![RAG Showcase seven approach flow phases](docs/diagrams/img/approach-flows.png)

*Parallel lane view of all seven approaches from shared corpus preparation through
retrieval, augmentation, generation, output shaping, and observed tradeoffs. Source:
[`docs/diagrams/approach-flows.html`](docs/diagrams/approach-flows.html). Full explanation:
[`docs/architecture.md`](docs/architecture.md); approach-by-approach internals:
[`docs/approaches.md`](docs/approaches.md).*

## 3. Quick Start

**Prerequisites.** This runs entirely on [Atlas](https://github.com/thekaveh/atlas), so Atlas's
requirements apply:

- **Docker** + **Docker Compose 2.24.4 or newer**, installed and running. The
  temporary disabled-service compatibility overlay uses Compose's `!reset` tag.
- The vendored **`infra/` submodule initialized**: `git submodule update --init --recursive`.
- Host tools **`uv`** and **`python3`** (Atlas's bootstrapper and the host-side corpus fetch use them).
- An Atlas-supported LLM backend. The manifest commits `LLM_PROVIDER_SOURCE: auto`
  (atlas#753), so each host resolves the best source — an existing host Ollama if
  installed, else a container — with no per-run flag. To pin one, edit the manifest
  or pass `--llm-provider-source` to `infra/start.sh` (an operator flag wins).
- Disk/RAM/headroom for the `gen-ai-rag` stack plus whichever local models you
  choose. The default local run asks Atlas to activate `mistral-small3.2:24b`
  for LightRAG extraction and uses Atlas's default `qwen3.6:latest` for graph
  keyword and query calls. See the
  [hardware sizing guide](docs/hardware.md) for minimum and recommended profiles.

```bash
./scripts/start-all.sh
```

This selects the parent-owned `atlas.consumer.yml`, runs Atlas's native headless
env backfill, manifest-aware Compose validation, and consumer doctor, then starts
Atlas with `--no-tui --detach`. The manifest sets durable
`BASE_PORT: auto`, so Atlas resolves a completely free 110-port block below the OS
dynamic/private range once and keeps it **stable across restarts** (persisted to
`infra/.env`); set `RAG_SHOWCASE_BASE_PORT` to pin a specific block instead (Atlas
fails before startup if it is occupied). The run prints the live Open WebUI URL when
it finishes, and every port can be re-derived from `infra/.env`. It passes project
name `rag-showcase`. The
manifest registers the project identity, branding, `config/atlas.env.user`,
    external Compose overlay, backend plugin root, Ollama model sidecar, and
    dataset-specific RAG ingestion profiles without tracked Atlas modifications or
    a `_user` symlink. Atlas applies the showcase
project and brand metadata (`rag-showcase-*` resources), waits on Compose health,
and returns before the script continues with the `gen-ai-rag` services (LightRAG,
TEI reranker, Weaviate, Neo4j, n8n, Open WebUI, and LiteLLM). The wrapper disables
    the hardware-dependent Docling source; Atlas therefore falls through to its
    plain-text parser and uses the profile's Chonkie recursive chunker. Atlas derives
    dependency enablement from service manifests, targets only enabled services,
    and returns its detached health summary before the wrapper continues,
    assembles the corpus on the host (`corpus/fetch_corpus.py`), waits for model
    readiness (embed + chat), submits the `showcase_default` Atlas ingestion job,
    builds only the approach-specific contextual index from Atlas-written chunks,
    and prints the Open WebUI URL. Atlas compiles the consumer-declared LiteLLM
    aliases into `config.yaml` before the proxy boots, so they are discoverable in
    `/v1/models` at startup with no consumer-side reconcile or proxy restart.
On a fresh checkout, Atlas renders its initial bootstrap banner before applying
the consumer manifest, so that first banner can retain Atlas artwork; subsequent
starts use the configured RAG-SHOWCASE logo. Atlas classifies a fully converged
successful one-shot race. If Compose returns while other services are still
starting, the wrapper accepts only that exact exited-zero signature and waits for
the same strict state; missing, unhealthy, or nonzero-exit services still fail.
If you use local models, the first run may
download several GB, so it takes a while. Then open the printed URL, start a multi-model chat, and select:
`vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`,
`n8n-adaptive-rag`, `lazy-graph-rag`. Stop everything with `./scripts/stop-all.sh`.

The explicitly selected experimental aliases are `lazy-graph-rag`,
`lazy-graph-rag-fast`, `lazy-graph-rag-balanced`, and `lazy-graph-rag-wide`.
They build an LLM-free concept graph from `RagBase` chunks. The base and its
flavors join the measured ladder with `--include-flavor-tier`; the ad hoc default
matrix remains the canonical six for backward compatibility.

The detached startup is the authoritative effective-config check: Atlas applies
the wrapper's fixed LightRAG container, TEI CPU, and Docling-disabled source flags,
revalidates the resolved stack, and only then starts the enabled Compose services.
Compute sources are committed in `atlas.consumer.yml` (`profile: dev` plus
`env.values`: `LLM_PROVIDER_SOURCE: auto`, LightRAG container, TEI CPU, Docling
disabled), so the start passes no per-run source flags and is host-correct on every
machine. An alternate `ATLAS_CONSUMER_MANIFEST` can change models, branding, sources,
and other consumer values.

The `n8n-adaptive-rag` workflow is checked in at
[`n8n/adaptive-rag.workflow.json`](n8n/adaptive-rag.workflow.json) and declared in
`atlas.consumer.yml`. Atlas validates, namespaces, imports, activates, and probes the
workflow during startup — including activation with no `N8N_API_KEY`
([Atlas #720](https://github.com/thekaveh/atlas/issues/720)), so `start-all.sh`
performs no manual publish or n8n restart. See [`n8n/README.md`](n8n/README.md) for
the ownership, lifecycle, and tuning contract.

For the full corpus (MultiHop-RAG + keyword docs), `python3 -m pip install datasets`
on the host before running; without it, ingestion uses only the bundled keyword docs, so
the thematic / multi-hop demo queries have little to work with — see
[`corpus/README.md`](corpus/README.md).

## 4. The Seven Approaches

| Model | Approach | Designed to win on |
|-------|----------|--------------------|
| [`vanilla-rag`](docs/approaches.md#3-vanilla-rag) | dense top-k → stuff → one call (baseline) | — (the control) |
| [`hybrid-rag`](docs/approaches.md#4-hybrid-rag) | Weaviate hybrid retrieval (BM25+dense) → TEI rerank; **not graph RAG** | exact keyword / ID queries |
| [`contextual-rag`](docs/approaches.md#5-contextual-rag) | Anthropic Contextual Retrieval over context-prefixed chunks | context-starved chunks |
| [`graph-rag`](docs/approaches.md#6-graph-rag) | Atlas LightRAG over extracted entities, relationships, and vector context | graph-shaped relationship questions |
| [`agentic-rag`](docs/approaches.md#7-agentic-rag) | ReAct loop over vector + graph tools | multi-hop / comparative questions |
| [`n8n-adaptive-rag`](docs/approaches.md#8-n8n-adaptive-rag) | low-code Adaptive-RAG workflow (routes by complexity) | mixed simple+complex batches |
| [`lazy-graph-rag`](docs/approaches.md#9-experimental-lazy-graph-rag) | deterministic concept graph + budgeted query-time expansion | graph-shaped data under a lower indexing budget |

The last column is the design intent behind each demo query family, not a measured
result — several intended contrasts did not materialize in the committed runs (the
measured per-query winners live in
[`docs/dataset-complexity-report.md`](docs/dataset-complexity-report.md) §4).

For exact internal steps, dependencies, tuning variables, and current measured
performance for each approach, see [`docs/approaches.md`](docs/approaches.md).

### 4.1 Experimental status

[`lazy-graph-rag`](docs/lazy-graph-rag.md) combines vector seeds with deterministic,
budgeted concept-graph expansion. It is a separate experimental approach, not a
LightRAG flavor. In the 2026-07-17 base-approach ladder it tied for third on
baseline, ranked first on graph-native, and tied for second on cyber-threat data.
It remains
experimental and off by default while its lightweight concept extraction and
co-occurrence semantics are evaluated on additional corpora.

## 5. Repository Layout

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

## 6. Configuration (environment variables)

These environment variables configure the showcase at runtime. The plugin reads
most of them; the LightRAG role values are consumed by Atlas from the manifest's
`config/atlas.env.user`, while the Ollama sidecar is declared directly in
`atlas.consumer.yml`. Most are already injected by Atlas's backend or
by the showcase's compose overlay (`compose/rag-overlay.yml`); none need to be set
by hand for the default `start-all.sh` flow.

[`backend_plugins/rag/plugin.yml`](backend_plugins/rag/plugin.yml) is the
Atlas-validated source of truth for the plugin's `/rag` route root, health path,
auth policy, typed environment contract, and service dependencies. The table
below expands that operator contract with adjacent Atlas and startup settings.

| Variable | Default | Read by | Source |
|----------|---------|---------|--------|
| `LITELLM_BASE_URL` | `http://litellm:4000` | plugin LiteLLM client | Atlas backend env |
| `LITELLM_API_KEY` | — | plugin LiteLLM client, n8n workflow node | Atlas backend env |
| `BACKEND_INTERNAL_API_TOKEN` | — | Bearer used by LiteLLM aliases when invoking trusted backend plugin routes | Atlas `.env`; injected into LiteLLM by the consumer-model overlay |
| `LITELLM_MASTER_KEY` | — | External LiteLLM gateway authentication | Atlas `.env`; mapped to `LITELLM_API_KEY` in the backend |
| `WEAVIATE_URL` | `http://weaviate:8080` | vectors | Atlas backend env |
| `RAG_WEAVIATE_GRPC_PORT` | `50051` | vectors (in-network gRPC port; distinct from Atlas's host-published `WEAVIATE_GRPC_PORT`) | plugin manifest + overlay |
| `TEI_RERANKER_ENDPOINT` | `http://tei-reranker:80` | vectors (rerank) | overlay |
| `TEI_RERANKER_MAX_BATCH` | `32` | vectors (rerank request batch cap) | plugin manifest + overlay |
| `LIGHTRAG_ENDPOINT` | `http://lightrag:9621` | lightrag client | Atlas backend env |
| `LIGHTRAG_API_KEY` | — | lightrag client | Atlas backend env |
| `N8N_ADAPTIVE_WEBHOOK_URL` | `http://n8n:5678/webhook/adaptive-rag` | n8n approach | overlay |
| `RAG_ROLES_FILE` | `/app/plugins/rag/roles.yaml` | config | plugin manifest; supplied by `config/atlas.env.user` and overlay |
| `RAG_FLAVORS_FILE` | `/app/plugins/rag/flavors.yaml` | runtime flavor parameter loader | plugin manifest; supplied by `config/atlas.env.user` and overlay; aliases are declared in `atlas.consumer.yml` and drift-tested against this file |
| `RAG_INGESTION_PROFILE` | `showcase_default` | startup, Atlas ingestion job, collection selection | host env + overlay; dataset ladder sets the selected dataset id |
| `RAG_BASE_COLLECTION` | `RagBase_<profile>` | vanilla, hybrid, agentic vector tool, contextual post-step | derived by `start-all.sh`; override only with a matching Atlas profile target |
| `RAG_CONTEXTUAL_COLLECTION` | `RagContextual_<profile>` | contextual post-step and contextual-rag | derived by `start-all.sh` |
| `BACKEND_PLUGINS_DIR` | `/app/plugins` | plugin seam (Atlas) | overlay |
| `ATLAS_CONSUMER_MANIFEST` | `atlas.consumer.yml` | Atlas bootstrapper | host env; absolute path to the parent-owned consumer manifest |
| `LIGHTRAG_EXTRACT_LLM_MODEL` | `mistral-small3.2:24b` | LightRAG EXTRACT role | `config/atlas.env.user` |
| `LIGHTRAG_KEYWORD_LLM_MODEL` | `qwen3.6:latest` | LightRAG KEYWORD role | `config/atlas.env.user`; Atlas applies model-scoped `think:false` |
| `LIGHTRAG_QUERY_LLM_MODEL` | `qwen3.6:latest` | LightRAG QUERY role | `config/atlas.env.user`; Atlas applies model-scoped `think:false` |
| `LIGHTRAG_EMBEDDING_MODEL` | `nomic-embed-text` | LightRAG embedding model | `config/atlas.env.user` |
| `LIGHTRAG_EXTRACT_MAX_ASYNC_LLM` | `1` | LightRAG EXTRACT concurrency | `config/atlas.env.user` |
| `LIGHTRAG_EXTRACT_LLM_TIMEOUT` | `900` | LightRAG EXTRACT timeout seconds | `config/atlas.env.user` |
| `OLLAMA_CUSTOM_MODELS` | includes `mistral-small3.2:24b` | local Ollama model activation | compiled from `atlas.consumer.yml` `model_sidecars.ollama` |
| `LIGHTRAG_QUERY_ENABLE_RERANK` | `false` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_TOP_K` | `10` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_CHUNK_TOP_K` | `5` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_QUERY_MAX_TOTAL_TOKENS` | `12000` | LightRAG service fallback | Atlas query profile owns each alias; overlay supplies the service fallback |
| `LIGHTRAG_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG base Ollama context cap (used only when a LightRAG role is bound directly to Ollama) | overlay |
| `LIGHTRAG_EXTRACT_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG EXTRACT-role Ollama context cap | overlay |
| `LIGHTRAG_KEYWORD_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG KEYWORD-role Ollama context cap | overlay |
| `LIGHTRAG_QUERY_OLLAMA_LLM_NUM_CTX` | `8192` | LightRAG QUERY-role Ollama context cap | overlay |
| `RAG_SHOWCASE_SKIP_DEFAULT_INGEST` | `0` | `start-all.sh` (skips corpus assembly + the default Atlas ingestion job; the dataset ladder sets it automatically) | host env |

## 7. Documentation Index

| Document | Status | What it covers |
|----------|--------|----------------|
| [Design spec](docs/superpowers/specs/2026-06-25-rag-showcase-design.md) | Historical | The approved design: six approaches, architecture, corpus, phasing (predates implementation — see its deviations note) |
| [Implementation plan](docs/superpowers/plans/2026-06-25-rag-showcase.md) | Historical | The task-by-task implementation plan (Tasks 0–19, as-built) |
| [Approach flavors plan](docs/superpowers/plans/2026-07-02-approach-flavors.md) | Historical | Follow-on plan that added the tunable flavor alias system |
| [Atlas LightRAG alignment plan](docs/superpowers/plans/2026-07-02-atlas-lightrag-alignment.md) + [design](docs/superpowers/specs/2026-07-02-atlas-lightrag-alignment-design.md) | Historical | Follow-on plan/design that wired LightRAG role models through Atlas inputs |
| [Cyber threat dataset plan](docs/superpowers/plans/2026-07-03-cyber-threat-dataset.md) | Historical | Follow-on plan that added the bounded MITRE ATT&CK cyber-threat corpus rung |
| [Overview](docs/guide/overview.md) | Living | Concepts — how the seven approaches run under identical conditions, flavor aliases, and the fair-comparison guarantees |
| [Quick Start](docs/guide/quickstart.md) | Living | One-command bring-up, prerequisites, and driving the multi-model comparison in Open WebUI |
| [Architecture diagrams](docs/architecture.md) | Living | Detailed project architecture and seven-approach parallel flow diagrams |
| [System diagram (interactive)](docs/diagrams/architecture.md) | Living | Rendered full-system architecture diagram (HTML/SVG in an inline iframe) |
| [Approach flow diagram (interactive)](docs/diagrams/approach-flows.md) | Living | Rendered parallel-lane diagram of the seven approach flow phases (HTML/SVG in an inline iframe) |
| [Approach internals](docs/approaches.md) | Living | Step-by-step flow, dependencies, tuning variables, tradeoffs, and measured performance for every approach |
| [Approach flavor tuning](docs/approach-flavor-tuning.md) | Living | Open WebUI model aliases, benchmark flavor selection, and query-time versus index-time tuning knobs |
| [Evaluation methodology](docs/evaluation-methodology.md) | Living | Atlas/showcase ownership, evidence schema, resumable ladder, Ragas states, operational metrics, judge panel, and four-artifact contract |
| [Evaluation results and leaderboards](docs/evaluation-results.md) | Generated | Complete static base and flavor rankings for every approach and metric |
| [Hardware sizing](docs/hardware.md) | Living | Minimum and recommended hardware profiles for live stack, local models, and graph-heavy runs |
| [Atlas-reuse assessment](docs/atlas-reuse-assessment.md) | Living | What reused cleanly, friction found, recommendations for Atlas |
| [Dependency contract ledger](docs/dependency-contracts.md) | Living | Each consumed external dependency (LiteLLM, Weaviate, LightRAG, TEI, n8n, Atlas) and the exact pinned version its contract was verified against |
| [Atlas LightRAG role-model spec](docs/atlas-lightrag-role-model-spec.md) | Implemented upstream | Historical Atlas-side spec for first-class LightRAG EXTRACT/KEYWORD/QUERY model wiring |
| [Corpus](corpus/README.md) | Living | How to populate the corpus |
| [Dataset adapters](corpus/adapters/README.md) | Living | The dataset fetch/adapter CLIs (GDELT, OpenAlex, STaRK, MITRE cyber) behind the candidate real-world graph rungs |
| [Dataset complexity report](docs/dataset-complexity-report.md) | Living | Judge and canonical metric rankings by dataset complexity, with coverage and legacy fallback |
| [Live run result snapshots](docs/results/README.md) | Living | Artifact ledger for committed evidence, summaries, matrices, and panel judgments |
| [n8n workflow](n8n/README.md) | Living | Checked-in Adaptive-RAG workflow, Atlas seeding lifecycle, and workflow tuning knobs |
| [Live comparison](docs/comparison.md) | Living | Side-by-side results of all seven approaches + live-validation findings (`think:false`, LightRAG role/query tuning, graph-native corpus behavior) |

## 8. Development & Testing

```bash
uv run pytest                 # unit suite (mocked I/O) + integration tests (skip without the stack)
uv run pytest backend_plugins # unit tests only
make eval-check               # read-only preflight: are the eval's Atlas-infra deps up? (needs a started stack)
```

`make eval-check` confirms the evaluation's dependencies — the LiteLLM
aliases, Weaviate plus its ingested collections, LightRAG, the TEI reranker,
n8n, and the required Ollama models — are up and in order **without** running
any ingestion, approach, or the LLM judge. It exits non-zero if anything is
missing, so it is a cheap gate before an expensive matrix run.

The unit tests mock all external I/O and run without the stack. The
`tests/test_demo_matrix.py` integration tests exercise the live stack and
self-skip when LiteLLM is unreachable. With a started stack they derive the
published gateway and master key from `infra/.env` automatically, so a plain
`uv run pytest tests` works; export `LITELLM_BASE_URL` / `LITELLM_MASTER_KEY`
only to target a non-default gateway:

```bash
LITELLM_BASE_URL="http://other-host:4000" LITELLM_MASTER_KEY="sk-yourkey" \
  uv run pytest tests
```

## 9. Troubleshooting

- **First run looks stuck.** If you use Atlas's containerized Ollama source, it may
  be downloading several GB of local models; `start-all.sh` gates on model
  readiness, so let it finish. Watch progress: `docker logs -f "$(grep -E '^PROJECT_NAME=' infra/.env | tail -1 | cut -d= -f2-)-ollama-pull"`.
- **A model column never answers.** Confirm the Atlas-declared aliases are visible (`GET /v1/models`,
  or the LiteLLM model list). `n8n-adaptive-rag` additionally needs the Atlas-owned
  `atlas-consumer-adaptive-rag` workflow active. Re-run `./scripts/start-all.sh`;
  it verifies the real production webhook and applies the temporary no-API-key
  activation fallback when required. Do not manually import a second copy. See
  [`n8n/README.md`](n8n/README.md).
- **`contextual-rag` doesn't visibly win** on the context-starved query: that contrast needs
  Docling structure-aware chunking. The showcase wrapper explicitly disables Docling for a
  hardware-neutral default, so Atlas uses plain-text parsing plus the profile's recursive
  chunker; select an Atlas-supported Docling source to preserve document structure.
- **Stack fails to come up with a Supabase / Postgres auth error** — e.g. `lightrag-init` exits
  with `password authentication failed for user "supabase_admin"`. This is an **Atlas stack**
  matter (the Supabase DB role/secret wiring), *not* the showcase. The reliable fix is a clean
  reset so the Atlas Supabase DB re-initializes against the current secrets:
  `cd infra && ./stop.sh --cold` (this **wipes Atlas volumes/data**), then re-run
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
  [Atlas-reuse assessment](docs/atlas-reuse-assessment.md).
- **Integration tests skip.** `tests/test_demo_matrix.py` self-skips unless a live LiteLLM is
  reachable; with a started stack the gateway is derived from `infra/.env`
  automatically (see §8 for the non-default-gateway override).
- **Stop / reset:** `./scripts/stop-all.sh` to stop; `cd infra && ./stop.sh --cold` to stop **and**
  wipe all Atlas data.
