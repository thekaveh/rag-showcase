# 4.4 Atlas Reuse Assessment — RAG Showcase

A living record of how well Atlas served as reusable infra for this project.

## 1. What Reused Cleanly (Out of the Box)

- **Declarative LiteLLM consumer models:** `atlas.consumer.yml` declares all six
  base approaches and eight flavor aliases. Atlas validates endpoint ownership,
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
  LiteLLM aliases, and Ollama model sidecar from the parent repository. Atlas validates and
  launches the assembled integration without any symlink inside the submodule.

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
> The RAG package now also ships Atlas's optional `plugin.yml` contract. Its six
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
startup configuration. Rag-showcase now uses that contract exclusively during
normal operation. An idempotent exact-match reconciliation removes only unowned
rows created by the retired registration script, including both the historical
`/<approach>/v1` and current `/rag/<approach>/v1` route shapes. Because LiteLLM's
four workers retain per-process route caches, a changed reconciliation triggers
one proxy restart and a fresh zero-change verification.

### 2.4 In-container path mismatch

`backend_plugins` mounts at `/app/plugins` (not `/app/backend_plugins`). Running
the ingest script in the backend required:

- `PYTHONPATH=/app/plugins`
- Mounting `ingest/` and `corpus/` directories into the container

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
> disabled. Rag-showcase has not enabled the adapter by default; profile adoption
> and evaluation remain a separate tuning decision.

### 2.12 Disabled manifest services can be treated as enabled during dependency checks

Atlas `fe55e838`'s dependency manager uses hard-coded source/scale maps that do
not include newer manifest services such as Trino and Redpanda. It therefore
reports disabled Trino as enabled and rejects a RAG-track start when MinIO is
disabled. This is tracked upstream as
[Atlas #503](https://github.com/thekaveh/atlas/issues/503). Until a fixed Atlas
commit is pinned, `start-all.sh` explicitly enables MinIO; no Atlas source is
patched locally.

### 2.13 Disabled services can still be built during unrelated track startup

Atlas starts the full assembled Compose graph. Compose may build a missing local
image even when that service has `deploy.replicas: 0`, so the disabled Asset
Baker's failing Blender download blocked the RAG track. Atlas-wide service
selection is tracked in [Atlas #504](https://github.com/thekaveh/atlas/issues/504),
and the Asset Baker artifact itself in
[Atlas #505](https://github.com/thekaveh/atlas/issues/505). The showcase overlay
temporarily removes the entire disabled `asset-baker` service from its resolved
Compose project; the service remains out of the RAG track.

### 2.14 Existing local images can remain stale after a submodule upgrade

Atlas uses `docker compose up --force-recreate`, which recreates containers but
does not rebuild an existing local image after its Dockerfile, requirements, or
source changes. During this upgrade, a June 29 backend image lacked Celery added
to Atlas on July 3 and restart-looped against the July 11 source mount. A one-time
`docker compose build backend` restored parity. Automatic source-drift detection
is tracked in [Atlas #506](https://github.com/thekaveh/atlas/issues/506).

### 2.15 Detached startup can reject an exited-zero init service

Atlas's detached path can return immediately when `docker compose up --wait`
reports that an expected one-shot init container exited, even when its exit code
is zero. That bypasses Atlas's later one-shot-aware status classifier and turns a
fully converged stack into a false startup failure. This is tracked in
[Atlas #508](https://github.com/thekaveh/atlas/issues/508).

The showcase keeps Atlas's detached result authoritative. Only after a nonzero
result with Atlas's exact exited-zero failure signature,
`scripts/verify_atlas_runtime.py` inspects containers in the `rag-showcase`
Compose project. It accepts only the fixed `gen-ai-rag` topology plus the
selected provider's required services (including `ollama` and `ollama-pull` for
container-backed Ollama), with every long-lived service running and healthy
(where a healthcheck exists) and every expected init service exited zero.
Missing, starting, unhealthy, or nonzero-exit services remain failures. Remove
this fallback after pinning an Atlas revision that performs the same
classification before returning.

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
  `litellm_models` support. The showcase now owns all fourteen route aliases in
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
- **Derive dependency enablement from service manifests** (§2.12): remove the
  hard-coded source/scale mapping so disabled and newly added services are
  interpreted consistently (Atlas #503).
- **Exclude disabled local builds from startup** (§2.13): launch only the
  resolved enabled service set so unrelated build failures cannot block a track
  (Atlas #504); separately restore the pinned Asset Baker artifact (Atlas #505).
- **Rebuild stale local images after source upgrades** (§2.14): detect build-context
  drift and refresh enabled images without rebuilding unchanged services (Atlas #506).
- **Classify successful one-shots before failing detached startup** (§2.15): when
  Compose reports an exited service, inspect expected init containers first and
  treat exit code zero as success while preserving failures for nonzero exits or
  unhealthy long-lived services (Atlas #508).

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
