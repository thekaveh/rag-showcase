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

## 3. Recommendations for Atlas

- **Upstream the backend plugin seam** as a documented downstream-routes extension
  point (symmetric to the `_user/` compose overlay). It adds minimal complexity
  and is both RAG-agnostic and generally useful.
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

## 4. Open Items (Pending Live End-to-End Run)

Quality of local-first LightRAG extraction and agentic tool-calling:

- LightRAG graph extraction (Atlas-side LLM; gen-ai-rag default `qwen3.6:latest`)
- `qwen3.6:latest` agentic tool-calling

These will be assessed after the full stack is brought up on a local machine.
Placeholder marked intentionally open, not a silent gap.
