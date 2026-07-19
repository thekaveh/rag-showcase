# 4.4 Atlas Reuse Assessment — RAG Showcase

A living record of how well Atlas served as reusable infra for this project.

## 1. What Reused Cleanly (Out of the Box)

- **Declarative LiteLLM consumer models:** `atlas.consumer.yml` declares all seven
  base approaches and twelve flavor aliases. Atlas validates endpoint ownership,
  compiles model rows before LiteLLM starts, and exposes the same aliases to Open
  WebUI and API clients without database registration calls.
- **The `gen-ai-rag` track:** Brings up Weaviate + Neo4j + LightRAG + TEI
  reranker + Docling + n8n + Open WebUI in a single flag, all pre-wired into the
  base stack. Rag-showcase explicitly disables Docling for a hardware-neutral
  default, while n8n now needs no out-of-track source override.
- **Backend's pre-wired environment:** LiteLLM/Weaviate/Neo4j/Redis/Docling/
  LightRAG URLs and credentials were already plumbed into the backend; our plugin
  read them directly with zero re-plumbing.
- **Open WebUI multi-model chat:** Served as the comparison frontend without
  requiring any custom UI implementation.
- **The consumer-manifest seam:** `atlas.consumer.yml` now registers project and
  brand metadata, the env file, external Compose overlay, backend plugin root,
  LiteLLM aliases, Ollama model sidecar, and the adaptive n8n workflow from the
  parent repository. Atlas validates and launches the assembled integration without
  any symlink or workflow bind mount inside the submodule.

## 2. Friction Found / Seams Added

### 2.1 Backend plugin seam (the one Atlas change)

Atlas's backend had no extension point for downstream routes. We added
**`plugin_seam.py`**: a generic loader that includes router packages found in
`$BACKEND_PLUGINS_DIR` and installs that directory's `requirements.txt`. This seam
contains no RAG-specific logic and is a **strong candidate to upstream** as a
documented downstream-routes extension point (symmetric to the `_user/` compose
overlay).

> **Resolved upstream.** Atlas `cd7aab7` (#162; documented in #164, `6fd482b`) upstreamed this exact seam
> (`services/backend/app/app/plugin_seam.py`, #162/#164) — same `BACKEND_PLUGINS_DIR`
> contract: load each immediate package exposing a module-level `router`,
> pip-install its `requirements.txt`, no-op when the dir is absent. The showcase no
> longer needs a fork-side seam; the plugin loads through Atlas's **native** seam via
> the unchanged compose overlay (`BACKEND_PLUGINS_DIR=/app/plugins` + the
> `backend_plugins/` mount). The override mechanism is identical — only the seam's
> provider moved from the fork to upstream.
>
> The RAG package now also ships Atlas's optional `plugin.yml` contract. Its seven
> approach routes share `/rag`, with `/rag/health`, inherited Kong auth, typed
> configuration, and dependency metadata validated by consumer doctor before
> startup and by the backend before import.

### 2.2 Client-library version floors

Atlas's backend image ships `weaviate-client` (`>=4.22.0` at the audited
submodule pin) and `neo4j` (`>=5.18.0`), so the RAG client libraries are present
out of the box. The plugin's `requirements.txt` range `weaviate-client>=4.9,<5`
is therefore a compatibility cap, not a newer floor — Atlas's own install already
satisfies it, so no startup reinstall normally happens. The plugin does not use
`neo4j` directly — it reaches the graph only via LightRAG over HTTP — so it
neither installs nor imports it.

### 2.3 Custom LiteLLM endpoint ownership

The original implementation stored custom endpoint rows through LiteLLM's admin
API because Atlas had no consumer-owned alias contract. That made ownership
implicit and left persisted duplicates during migration. Atlas #411 resolved the
gap with versioned `litellm_models` declarations, approved endpoint templates,
derived ownership metadata, collision checks, secret references, and generated
startup configuration. Rag-showcase now uses that contract exclusively. Atlas compiles the declared
`litellm_models` into `config.yaml` before the proxy boots, so the aliases are
discoverable in `/v1/models` at startup with no consumer-side reconciliation or
proxy restart.

### 2.4 In-container path mismatch

> **Resolved as a generic/local split.** `backend_plugins` still mounts at
> `/app/plugins`, while the corpus and the small contextual post-processor mount
> under `/app`. Generic ingestion no longer imports showcase code: Atlas compiles
> `rag_ingestion_profiles`, mounts them into its backend, and owns parsing,
> chunking, base vectors, LightRAG upload, and drain. The local post-step uses
> `PYTHONPATH=/app/plugins:/app` only to derive the contextual collection.

### 2.5 FastAPI version sensitivity

The seam test's `r.path` route introspection only works on FastAPI `<0.137`
(which Atlas pins). A relaxed version pin would break this introspection pattern.

### 2.6 Overlay slot location and setup

> **Resolved upstream.** The original integration symlinked the parent-owned
> Compose fragment into Atlas's gitignored `_user/` slot. Atlas's consumer
> manifest now accepts external `compose_overlays` and `backend_plugins` paths,
> so `atlas.consumer.yml` owns that registration directly and
> `scripts/setup-overlay.sh` has been removed. `start-all.sh` only removes the
> exact legacy symlink left by an older checkout; it refuses to touch an
> unexpected symlink or regular file.

### 2.7 Non-interactive detached startup

> **Resolved upstream.** Atlas now exposes `--no-tui --detach` (alias
> `--no-follow`) for automation. It runs the normal start pipeline, waits for
> Compose health, prints a final status summary, and exits nonzero when the final
> state is unhealthy. Rag-showcase now invokes that mode directly after Atlas's
> headless env backfill, manifest-aware Compose validation, and consumer doctor;
> it no longer backgrounds or kills the bootstrapper process. Detached startup
> performs the authoritative effective-env validation after applying the
> manifest and source flags.

### 2.8 Host-Ollama provider option

> **Resolved upstream.** The updated Atlas submodule exposes
> `LLM_PROVIDER_SOURCE=ollama-localhost`, resolves
> `LITELLM_OLLAMA_UPSTREAM` to the host Ollama endpoint, and lets LiteLLM import
> host-pulled models. Rag-showcase no longer needs the historical `qwen3.6-moe`
> runtime alias to route around container Ollama.

### 2.9 LightRAG defaults extraction to the CPU model, then silently builds an empty graph

`lightrag-init/scripts/resolve-models.py` resolves the extraction LLM to
`LITELLM_DEFAULT_MODEL` (= `ollama/qwen3.6:latest`, CPU) unless `LIGHTRAG_LLM_MODEL`
is set. On a CPU-only host this hits the extraction worker timeout (240-480 s),
produces **zero entities**, yet `/health` reports healthy, so `graph-rag` can
silently return "no context" with no surfaced error.

The showcase now configures LightRAG role models through Atlas's public
`LIGHTRAG_EXTRACT_LLM_MODEL`, `LIGHTRAG_KEYWORD_LLM_MODEL`, and
`LIGHTRAG_QUERY_LLM_MODEL` inputs. That keeps role selection independent of the
chosen provider source.

### 2.10 LightRAG role-specific model wiring

> **Resolved upstream.** Atlas now exposes `LIGHTRAG_EXTRACT_*`,
> `LIGHTRAG_KEYWORD_*`, and `LIGHTRAG_QUERY_*` inputs and maps them to
> LightRAG's native runtime role variables. Rag-showcase now sets those public
> Atlas inputs through the parent-owned `config/atlas.env.user` overlay instead of
> carrying a compose override that writes native LightRAG variables directly.

### 2.11 LightRAG query rerank does not match Atlas's TEI reranker API

After graph indexing was fixed, `graph-rag` still returned one-word answers and took
~31 s/query. LightRAG logs showed the query-time rerank path calling the configured
TEI endpoint with a Jina-style payload; TEI rejected it with `422 missing field
texts`, after retries. Disabling LightRAG query rerank and reducing query fanout
(`top_k=10`, `chunk_top_k=5`, `max_total_tokens=12000`) produced usable answers.

> **Resolved upstream.** Atlas leaves direct LightRAG->TEI rerank disabled by
> default, exposes concrete query fanout defaults, and now ships an authenticated
> backend adapter (`POST /lightrag/rerank`). Operators can opt in with
> `LIGHTRAG_RERANK_ADAPTER_ENABLED=true` while keeping the incompatible direct path
> disabled. Rag-showcase enables the adapter through its consumer env and exposes
> one opt-in `graph-rag-rerank` query profile beside rerank-disabled controls. Atlas
> #654 now validates that consumer env overlay without a bootstrap `.env` mutation.

The 2026-07-17 flavor run then found a second adapter-boundary case: LightRAG
submitted 43 candidates while TEI's configured client limit is 32. Atlas
[#713](https://github.com/thekaveh/atlas/issues/713) and
[#714](https://github.com/thekaveh/atlas/pull/714) now batch adapter requests,
remap indexes globally, enforce one total timeout budget, and fail the complete
request if any batch fails. Rag-showcase advanced its submodule to that merged
fix and validated the same request as 32- and 11-document TEI batches.

### 2.12 Disabled manifest services can be treated as enabled during dependency checks

> **Resolved upstream.** Atlas #503 now derives dependency enablement from service
> manifest source metadata. Rag-showcase no longer enables MinIO solely to satisfy
> a disabled Trino dependency.

### 2.13 Disabled services can still be built during unrelated track startup

> **Resolved upstream.** Atlas #504 now computes the enabled-service target set
> from the rendered project and passes it to build and startup. The showcase no
> longer removes `asset-baker` from its Compose overlay. Atlas #505 still tracks
> that service's own Blender artifact independently of this RAG track.

### 2.14 Existing local images can remain stale after a submodule upgrade

Atlas uses `docker compose up --force-recreate`, which recreates containers but
does not rebuild an existing local image after its Dockerfile, requirements, or
source changes. During this upgrade, a June 29 backend image lacked Celery added
to Atlas on July 3 and restart-looped against the July 11 source mount. A one-time
`docker compose build backend` restored parity. Automatic source-drift detection
is tracked in [Atlas #506](https://github.com/thekaveh/atlas/issues/506).

### 2.15 Detached startup can reject an exited-zero init service

> **Partially resolved upstream.** Atlas #508 inspects the rendered service state
> when `docker compose up --wait` returns nonzero and accepts a fully converged
> snapshot. A 2026-07-13 live run exposed a remaining timing case: Compose reports
> an exited-zero `n8n-init` while otherwise healthy long-lived services still have
> `starting` health. Atlas inspects once and returns failure instead of waiting for
> that snapshot to converge.

The showcase therefore retains a narrow fallback. It activates only when Atlas's
output contains both the exact exited-zero signature and failed-start summary,
then waits for the fixed RAG topology. Every long-lived service must become
running and healthy and every expected one-shot must exit zero; missing,
unhealthy, restarting, timed-out, or nonzero-exit services still fail. Remove the
fallback when Atlas performs this bounded convergence wait itself.

### 2.16 n8n no-API-key seeding does not publish active workflows

Atlas's consumer workflow contract now validates, namespaces, imports, reconciles,
and probes the Adaptive-RAG workflow. A fresh-volume validation against n8n 2.28.2
found one remaining lifecycle gap: with `N8N_API_KEY` unset, the CLI import persists
normalized `active: true` JSON as inactive. The production webhook remains 404, and
the best-effort seed reports the failed probe without failing stack startup. A
restart alone does not change the state.

The showcase temporarily publishes only the Atlas-owned
`atlas-consumer-adaptive-rag` id, reloads n8n, and then requires a successful real
webhook answer. Atlas #514 tracks moving the activation/reload step upstream;
the manifest and workflow source will remain unchanged when that shim is removed.

### 2.17 Generic ingestion lifecycle

> **Resolved upstream.** Atlas #413 added versioned consumer RAG ingestion profiles,
> safe corpus mounts, deterministic profile revisions, phase-level job records,
> idempotent Weaviate writes, LightRAG upload/drain, cancellation, and a headless API.
> Rag-showcase now declares one profile per dataset and uses that API from both
> default startup and the dataset ladder. The former all-in-one `ingest/ingest.py`
> and bespoke LightRAG drain polling are removed.

The one retained local phase is intentional rather than infrastructure duplication:
`contextual-rag` generates LLM blurbs from Atlas-written chunks and writes a separate
`RagContextual_<profile>` collection. Matrix and judgment snapshots now carry the
Atlas ingestion id, profile revision, and content digest. Historical snapshots
remain immutable and therefore do not claim job provenance they never recorded.

### 2.18 Generated backend profile mounts collided with the `/app` source bind

The first live consumer-profile smoke passed Atlas manifest validation and doctor,
then failed while Docker Desktop created the backend container. Atlas #413 and
#414 generate single-file mounts at `/app/rag-ingestion-profiles.json` and
`/app/lightrag-query-profiles.json`, but the backend already bind-mounts its source
directory at `/app`. Docker Desktop/VirtioFS rejects that nested file mount as an
outside-rootfs mountpoint.

> **Resolved upstream.** Atlas #533 moved both registries to the dedicated
> read-only `/atlas-consumer-config/` path. The showcase consumes that contract
> directly and does not carry an unvalidated private registry.

### 2.19 Generic ingestion runtime and LightRAG upload contract

The first Atlas-job validation on the corrected mount path found two independent
runtime mismatches: the backend image's `appuser` had no writable home for the
Chonkie/tokie tokenizer cache, and Atlas sent LightRAG's retired `description`
field instead of the 1.5.x-required `file_source`. Both failures occurred after
manifest validation and therefore needed real ingestion evidence.

> **Resolved upstream.** Atlas #602 creates `/home/appuser` in the backend image,
> sends `file_source`, and records bounded upstream response bodies on failures.
> Rag-showcase pinned Atlas `3c33250b` for that validation and removed its temporary cache environment
> override. Live job `7127dcc3-7a45-40ad-ae28-5b547cf0bc8b` then completed all
> discover/parse/chunk/embed/vector-write/upload/drain/finalize phases.

### 2.20 LightRAG drain polling failed on transient status timeouts

> **Resolved upstream.** Atlas #673 retries timeout and transport failures within
> the profile drain deadline, preserves cancellation and lease heartbeats, and
> records poll/retry evidence. Rag-showcase again declares
> `wait_for_extraction: true`; its temporary second drain loop was removed.

### 2.21 Consumer rerank capability validation ignored the consumer env overlay

> **Resolved upstream.** Atlas #654 computes the effective rerank-adapter flag from
> the merged consumer environment before validating LightRAG query profiles. The
> showcase no longer copies that flag into `infra/.env` before preflight.

### 2.22 Project stop could terminate host-global managed runtimes

> **Resolved upstream.** Atlas #655 makes project-scoped stop preserve shared host
> runtimes unless the operator explicitly requests global shutdown. The showcase
> delegates teardown to `infra/stop.sh --project rag-showcase` instead of assembling
> a private Compose-down command.

### 2.23 Native LightRAG roles can bypass catalog request defaults

Atlas #658 remains open. A native Ollama KEYWORD or QUERY binding would bypass the
catalog-scoped `think:false` default. The showcase therefore keeps those two roles
behind LiteLLM and sends only the non-reasoning EXTRACT role directly to Ollama.
This is role-scoped and does not apply request parameters globally.

## 3. Recommendations for Atlas

- **(Resolved)** Originally: *upstream the backend plugin seam* as a documented
  downstream-routes extension point (symmetric to the `_user/` compose overlay).
  Atlas `cd7aab7` did exactly this (#162; documented in #164, `6fd482b`): the generic
  `plugin_seam.py` now ships in the backend image with the same `BACKEND_PLUGINS_DIR`
  contract the showcase targets, so no fork-side seam is needed — the unchanged
  compose overlay drives Atlas's native seam.
- **(No action needed) RAG client libraries** — Atlas's `gen-ai-rag` backend
  already ships `weaviate-client` and `neo4j`; the plugin's own range is a
  compatibility cap that Atlas's install already satisfies. (Originally filed as
  a gap — corrected after checking the vendored image's `requirements.txt`.)
- **(Resolved) Consumer-owned LiteLLM aliases:** Atlas #411 added declarative
  `litellm_models` support. The showcase now owns all nineteen route aliases in
  `atlas.consumer.yml`; Atlas renders and validates them without admin API calls.
- **(Resolved) Load parent-owned Compose overlays directly:** Atlas's
  `atlas.consumer.yml` `compose_overlays` block supersedes the proposed
  `--extra-compose` flag and removes the `_user/` symlink requirement.
- **(Resolved) Support detached scripted startup** (§2.7): Atlas now provides
  `--no-tui --detach` / `--no-follow` with health-gated exit status and an optional
  JSON summary.
- **(Resolved) Add a host-Ollama provider option** (§2.8): Atlas now supports
  `LLM_PROVIDER_SOURCE=ollama-localhost`.
- **(MED) Surface LightRAG extraction failures** (§2.9): a timed-out / empty-graph
  extraction should show in `/health` or as a loud error, not just a log WARNING.
  Document that graph extraction needs a GPU-class (ideally non-reasoning) model and
  how to set `LIGHTRAG_LLM_MODEL`.
- **(Resolved) Expose LightRAG role-specific models** (§2.10): Atlas now maps
  `LIGHTRAG_EXTRACT_LLM_MODEL`, `LIGHTRAG_KEYWORD_LLM_MODEL`, and
  `LIGHTRAG_QUERY_LLM_MODEL` to LightRAG's native runtime vars.
- **(Resolved) Adapt LightRAG query rerank for TEI** (§2.11): Atlas defaults the
  incompatible direct path off and provides an opt-in authenticated backend adapter.
- **(Resolved) Derive dependency enablement from service manifests** (§2.12):
  Atlas #503 now interprets disabled and newly added services consistently.
- **(Resolved) Exclude disabled local builds from startup** (§2.13): Atlas #504
  launches only the resolved enabled service set. Atlas #505 separately tracks
  the Asset Baker artifact.
- **Rebuild stale local images after source upgrades** (§2.14): detect build-context
  drift and refresh enabled images without rebuilding unchanged services (Atlas #506).
- **(Resolved upstream with bounded consumer compatibility) Successful one-shot
  convergence:** Atlas #508 classifies the benign zero-exit signature. The showcase
  retains a stricter bounded wait for the observed intermediate `starting` state;
  it does not broaden accepted failures.
- **Publish active n8n workflows without an API key** (§2.16): honor the effective
  activation policy on fresh volumes, coalesce any required reload, and make required
  webhook readiness deterministic (Atlas #514).
- **(Resolved) Provide generic RAG ingestion jobs** (§2.17): Atlas #413 now owns
  discover/parse/chunk/embed/vector-write/LightRAG-upload/drain/finalize; the
  showcase retains only its approach-specific contextual transform.
- **(Resolved) Move generated backend registries outside `/app`** (§2.18): Atlas
  #533 mounts ingestion and LightRAG query profile registries under the reserved
  `/atlas-consumer-config/` directory.
- **(Resolved) Make generic ingestion runnable against LightRAG 1.5** (§2.19):
  Atlas #602 supplies a writable backend runtime home, uses `file_source`, and
  retains bounded upstream error evidence.
- **(Resolved) Retry transient LightRAG drain polls** (§2.20): Atlas #673 owns the
  bounded retry/deadline/evidence contract; no consumer drain remains.
- **(Resolved) Honor consumer env during rerank validation** (§2.21): Atlas #654
  removed the showcase's bootstrap mutation.
- **(Resolved) Preserve shared managed hosts on project stop** (§2.22): Atlas #655
  lets the showcase use native project-scoped teardown.
- **Preserve model request defaults across native LightRAG roles** (§2.23): Atlas
  #658 remains open; the LiteLLM transport selection is the bounded workaround.

## 4. Live End-to-End Run — Resolved (2026-07-01)

The first live e2e run was completed (see [comparison.md](comparison.md)). The
previously-open items are now assessed:

- **LightRAG graph extraction** — fixed locally for the 11-document curated subset by
  using role-specific LightRAG settings and a non-reasoning extraction model
  (§2.10). The full corpus is still an expensive graph-indexing stress test.
- **LightRAG graph query** — fixed locally enough to include `graph-rag` in the scored
  six-way run by disabling LightRAG query rerank and reducing graph query fanout
  (§2.11). Quality remains uneven and slower than text/vector approaches.
- **Agentic tool-calling (qwen3.6 MoE)** — `MAX_STEPS=4` is too low for the reasoning
  model to converge on multi-hop/synthesis queries; 3/6 queries hit the step cap. The
  empty graph tool (above) compounded it. It answered well on single-shot queries
  (keyword, context_starved) via the vector tool.
- **Text approaches (vanilla / hybrid / contextual)** — worked well and differentiated
  modestly on the curated corpus (full results in `comparison.md`).

### 4.1 Atlas `fe55e838` baseline revalidation (2026-07-11)

- `scripts/start-all.sh` completed in service-only mode and verified every
  canonical and flavor alias.
- The live six-approach smoke suite passed: **8 tests passed**.
- A graph-native document was inserted through LightRAG, extraction drained, and
  `graph-rag` correctly joined Project Cedar's lead, dependent service, and
  disrupting incident with the inserted document cited.
- The stack was stopped normally after verification; data volumes were preserved.

### 4.2 Atlas `3c33250b` generic-ingestion validation (2026-07-14)

- `scripts/start-all.sh` converged all 27 enabled services and registered the
  then-current 18 aliases without a consumer-owned backend cache override.
- Atlas job `7127dcc3-7a45-40ad-ae28-5b547cf0bc8b` completed all eight phases for
  `graph_native`: 10 files discovered and parsed, 10 chunks, 10 vectors written,
  10 LightRAG uploads, a 320.5-second graph-extraction drain, and zero errors.
- The local contextual post-step read the Atlas chunks and produced 10 objects in
  `RagContextual_graph_native`; `RagBase_graph_native` also contained 10 objects.
- LightRAG reported no busy or pending work after drain. The shared Neo4j graph
  contained 455 nodes and 411 relationships after the preserved-volume run.
- The live canonical six-approach suite passed all **8 tests** in 92.72 seconds,
  including one non-empty, metrics-bearing answer through each public alias.
