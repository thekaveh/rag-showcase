# Atlas Reuse Assessment — RAG Showcase

A living record of how well Atlas served as reusable infra for this project.

## 1. What Reused Cleanly (Out of the Box)

- **LiteLLM service-as-a-model pattern:** Registered all six custom-`api_base`
  approaches via LiteLLM's `/model/new` admin API (`STORE_MODEL_IN_DB=True`) with
  **zero Atlas edits** for registration. Atlas's existing `lightrag` and
  `hermes-agent` model entries were the existence proof.
- **The `gen-ai-rag` track:** Brought up Weaviate + Neo4j + LightRAG + TEI
  reranker + Docling + OpenWebUI in a single flag, all pre-wired into the base
  stack.
- **Backend's pre-wired environment:** LiteLLM/Weaviate/Neo4j/Redis/Docling/
  LightRAG URLs and credentials were already plumbed into the backend; our plugin
  read them directly with zero re-plumbing.
- **OpenWebUI multi-model chat:** Served as the comparison frontend without
  requiring any custom UI implementation.
- **The `services/_user/` overlay slot:** Auto-discovered our compose fragment and
  merged it into the existing `backend` service via compose service-name
  merge — worked on first try.

## 2. Friction Found / Seams Added

### 2.1 Backend plugin seam (the one Atlas change)

Atlas's backend had no extension point for downstream routes. We added
**`plugin_seam.py`**: a generic loader that includes router packages found in
`$BACKEND_PLUGINS_DIR` and installs that directory's `requirements.txt`. This seam
contains no RAG-specific logic and is a **strong candidate to upstream** as a
documented downstream-routes extension point (symmetric to the `_user/` compose
overlay).

> **Resolved upstream.** Atlas `6fd482b` upstreamed this exact seam
> (`services/backend/app/app/plugin_seam.py`, #162/#164) — same `BACKEND_PLUGINS_DIR`
> contract: load each immediate package exposing a module-level `router`,
> pip-install its `requirements.txt`, no-op when the dir is absent. The showcase no
> longer needs a fork-side seam; the plugin loads through Atlas's **native** seam via
> the unchanged compose overlay (`BACKEND_PLUGINS_DIR=/app/plugins` + the
> `backend_plugins/` mount). The override mechanism is identical — only the seam's
> provider moved from the fork to upstream.

### 2.2 Client-library version floors

Atlas's backend image already ships `weaviate-client` (`>=4.0.0`) and `neo4j`
(`>=5.18.0`), so the RAG client libraries are present out of the box. The
plugin's `requirements.txt` pins a newer `weaviate-client>=4.9,<5` floor, so the
seam may reinstall weaviate-client at startup to satisfy it (a minor boot cost).
The plugin does not use `neo4j` directly — it reaches the graph only via LightRAG
over HTTP — so it neither installs nor imports it.

### 2.3 No `api_base` column in `public.llms`

`public.llms` has no `api_base` column and its `openai` provider routes to
`api.openai.com`. The table cannot express custom-endpoint models. The
`/model/new` admin API was the correct channel and worked well; this pattern
should be **documented for Atlas** as the preferred way to register custom
OpenAI-compatible endpoints.

> **Resolved upstream.** Atlas `d085f09` removed `public.llms` entirely — model
> source-of-truth moved to per-service YAML — so this table-level limitation no
> longer applies. The `/model/new` admin API remains the channel the showcase uses.

### 2.4 In-container path mismatch

`backend_plugins` mounts at `/app/plugins` (not `/app/backend_plugins`). Running
the ingest script in the backend required:

- `PYTHONPATH=/app/plugins`
- Mounting `ingest/` and `corpus/` directories into the container

### 2.5 FastAPI version sensitivity

The seam test's `r.path` route introspection only works on FastAPI `<0.137`
(which Atlas pins). A relaxed version pin would break this introspection pattern.

### 2.6 Overlay slot location and setup

The `_user/` overlay slot lives inside the Atlas submodule (which is gitignored
upstream). We symlink our fragment in via `scripts/setup-overlay.sh`, so the
showcase repo owns the compose-fragment file while the overlay slot remains under
Atlas's gitignore.

### 2.7 `start.sh`/`start.py` blocks non-interactive callers by tailing logs

Atlas's `start.py` brings the stack up detached (`up -d`), then ends by **following
logs** — `show_container_logs(follow=True)` at `bootstrapper/start.py:1832-1841`,
called unconditionally with only a `KeyboardInterrupt` handler. On a non-TTY caller
(this repo's `scripts/start-all.sh`, CI, any automation), `docker compose … logs -f`
blocks **forever**, so control never returns and the wrapper's downstream steps
(corpus ingest, model registration) never run. **This was why live e2e had never
been verified.** Workaround: after the stack is healthy, run ingest + register
directly via `docker exec`. (First confirmed via the live process tree: a wedged
`docker compose … logs -f` child of `start.py`.)

### 2.8 No host-Ollama provider option (macOS / Apple Silicon)

The `llm-provider` (Ollama) is `always_on` and **always containerized** — there is
no `--llm-provider-source` among Atlas's `--*-source` flags. On macOS, Docker
Desktop cannot pass through the Apple Metal GPU, so that container is **CPU-only**
and the default 24–38 GB local models are unusably slow (a 6000-char contextualize
call exceeded the 120 s client timeout). We re-pointed LiteLLM's chat model to the
**host** Ollama (`host.docker.internal:11434`, Metal-accelerated) via a `/model/new`
DB model (`qwen3.6-moe`). `OLLAMA_SCALE=0` can disable the container, but nothing
wires the host instance in its place.

### 2.9 LightRAG defaults extraction to the CPU model, then silently builds an empty graph

`lightrag-init/scripts/resolve-models.py` resolves the extraction LLM to
`LITELLM_DEFAULT_MODEL` (= `ollama/qwen3.6:latest`, CPU) unless `LIGHTRAG_LLM_MODEL`
is set. On a CPU-only host this hits the extraction worker timeout (240-480 s),
produces **zero entities**, yet `/health` reports healthy, so `graph-rag` can
silently return "no context" with no surfaced error.

The showcase now works around this locally by pointing LightRAG EXTRACT/KEYWORD/QUERY
directly at host Ollama and using `mistral-small3.2:24b` with a capped 8192-token
Ollama context. That successfully drained the 11-document curated graph build. The
full 41-file corpus remains a separate capacity/stress test.

### 2.10 Atlas does not expose LightRAG's role-specific model wiring

The deeper blocker (found 2026-06-30): Atlas configures LightRAG as a single-model
service (`LIGHTRAG_LLM_MODEL` → `LLM_MODEL`), while the pinned LightRAG v1.5.4 image
has native role-specific LLM settings: `EXTRACT_LLM_MODEL`, `KEYWORD_LLM_MODEL`, and
`QUERY_LLM_MODEL`. The reliable fix is not another global model override; it is to
expose LightRAG's native role variables so the call-heavy EXTRACT role can use a
medium, non-reasoning model independently of QUERY.

Rag-showcase carries a local compose override that sets those native role vars
directly for this repo without changing Atlas defaults. A shareable Atlas-side spec
is captured in [atlas-lightrag-role-model-spec.md](atlas-lightrag-role-model-spec.md).

### 2.11 LightRAG query rerank does not match Atlas's TEI reranker API

After graph indexing was fixed, `graph-rag` still returned one-word answers and took
~31 s/query. LightRAG logs showed the query-time rerank path calling the configured
TEI endpoint with a Jina-style payload; TEI rejected it with `422 missing field
texts`, after retries. Disabling LightRAG query rerank and reducing query fanout
(`top_k=10`, `chunk_top_k=5`, `max_total_tokens=12000`) produced usable answers.

*Net effect:* Atlas should either expose a LightRAG-compatible reranker binding for
the TEI service, disable LightRAG query rerank when the configured endpoint is TEI,
or document the required `/rerank` payload adapter.

## 3. Recommendations for Atlas

- **(Resolved)** Originally: *upstream the backend plugin seam* as a documented
  downstream-routes extension point (symmetric to the `_user/` compose overlay).
  Atlas `6fd482b` did exactly this (#162, documented in #164): the generic
  `plugin_seam.py` now ships in the backend image with the same `BACKEND_PLUGINS_DIR`
  contract the showcase targets, so no fork-side seam is needed — the unchanged
  compose overlay drives Atlas's native seam.
- **(No action needed) RAG client libraries** — Atlas's `gen-ai-rag` backend
  already ships `weaviate-client` and `neo4j`; the plugin only re-pins a newer
  `weaviate-client` floor. (Originally filed as a gap — corrected after checking
  the vendored image's `requirements.txt`.)
- **(Resolved)** Originally: *add an `api_base` column to `public.llms`* to express
  custom-endpoint models natively. Atlas has since removed `public.llms` outright
  (model source-of-truth moved to per-service YAML, `d085f09`); the showcase now
  registers its custom OpenAI-compatible endpoints via the `/model/new` admin API,
  which remains the supported pattern.
- **Add a `--extra-compose <file>` flag to `start.sh`** so consumers can add
  overlays without symlinking into the gitignored `_user/` slot.
- **(HIGH) Don't block non-interactive callers on `logs -f`** (§2.7). Guard
  `start.py`'s `show_container_logs(follow=True)` on `sys.stdout.isatty()`, or add a
  `--no-follow`/`--detach` flag, so scripted bring-ups return after the stack is
  healthy. This is the single change that unblocks automated end-to-end runs.
- **(MED-HIGH) Add a host-Ollama provider option** (§2.8): a `--llm-provider-source
  host` that points LiteLLM's ollama models' `api_base` at `host.docker.internal:11434`,
  or document the macOS path. The containerized Ollama is CPU-only on macOS.
- **(MED) Surface LightRAG extraction failures** (§2.9): a timed-out / empty-graph
  extraction should show in `/health` or as a loud error, not just a log WARNING.
  Document that graph extraction needs a GPU-class (ideally non-reasoning) model and
  how to set `LIGHTRAG_LLM_MODEL`.
- **(HIGH) Expose LightRAG role-specific models** (§2.10): map Atlas variables such as
  `LIGHTRAG_EXTRACT_LLM_MODEL`, `LIGHTRAG_KEYWORD_LLM_MODEL`, and
  `LIGHTRAG_QUERY_LLM_MODEL` to LightRAG's native runtime vars. Keep the current
  `LIGHTRAG_LLM_MODEL` fallback for backward compatibility. See the
  [role-model spec](atlas-lightrag-role-model-spec.md).
- **(MED-HIGH) Fix or disable LightRAG query rerank for TEI** (§2.11): the current
  LightRAG/Jina rerank client does not speak the same payload shape as the Atlas TEI
  reranker. Either provide an adapter, select a compatible rerank binding, or default
  LightRAG query rerank off when Atlas wires TEI directly.

## 4. Live End-to-End Run — Resolved (2026-07-01)

The first live e2e run was completed (see [comparison.md](comparison.md)). The
previously-open items are now assessed:

- **LightRAG graph extraction** — fixed locally for the 11-document curated subset by
  using role-specific host-Ollama settings and a non-reasoning extraction model
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
