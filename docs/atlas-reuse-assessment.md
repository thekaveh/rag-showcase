# Atlas Reuse Assessment — RAG Showcase

A living record of how well Atlas served as reusable infra for this project.

## What reused cleanly (out of the box)

- **LiteLLM service-as-a-model pattern:** Registered all six custom-`api_base` approaches via LiteLLM's `/model/new` admin API (`STORE_MODEL_IN_DB=True`) with **zero Atlas edits** for registration. Atlas's existing `lightrag` and `hermes-agent` model entries were the existence proof.

- **The `gen-ai-rag` track:** Brought up Weaviate + Neo4j + LightRAG + TEI reranker + Docling + OpenWebUI in a single flag, all pre-wired into the base stack.

- **Backend's pre-wired environment:** LiteLLM/Weaviate/Neo4j/Redis/Docling/LightRAG URLs and credentials were already plumbed into the backend; our plugin read them directly with zero re-plumbing.

- **OpenWebUI multi-model chat:** Served as the comparison frontend without requiring any custom UI implementation.

- **The `services/_user/` overlay slot:** Auto-discovered our compose fragment and merged it into the existing `backend` service via compose service-name merge—worked on first try.

## Friction found / seams added

### Backend plugin seam (the ONE Atlas change)
Atlas's backend had no extension point for downstream routes. We added **`plugin_seam.py`**: a generic loader that includes router packages found in `$BACKEND_PLUGINS_DIR` and installs that directory's `requirements.txt`. This seam contains no RAG-specific logic and is a **strong candidate to upstream** as a documented downstream-routes extension point (symmetric to the `_user/` compose overlay).

### Missing client libraries in gen-ai-rag backend
The `gen-ai-rag` backend image does not ship `weaviate-client` and `neo4j` Python libraries. Our plugin installs them via the seam's `requirements.txt` at startup. This keeps Atlas's base image lean but adds measurable boot latency.

### No `api_base` column in `public.llms`
`public.llms` has no `api_base` column and its `openai` provider routes to `api.openai.com`. The table cannot express custom-endpoint models. The `/model/new` admin API was the correct channel and worked well; this pattern should be **documented for Atlas** as the preferred way to register custom OpenAI-compatible endpoints.

### In-container path mismatch
`backend_plugins` mounts at `/app/plugins` (not `/app/backend_plugins`). Running the ingest script in the backend required:
- `PYTHONPATH=/app/plugins` 
- Mounting `ingest/` and `corpus/` directories into the container

### FastAPI version sensitivity
The seam test's `r.path` route introspection only works on FastAPI `<0.137` (which Atlas pins). A relaxed version pin would break this introspection pattern.

### Overlay slot location and setup
The `_user/` overlay slot lives inside the Atlas submodule (which is gitignored upstream). We symlink our fragment in via `scripts/setup-overlay.sh`, so the showcase repo owns the compose-fragment file while the overlay slot remains under Atlas's gitignore.

## Recommendations for Atlas

- **Upstream the backend plugin seam** as a documented downstream-routes extension point (symmetric to the `_user/` compose overlay). It adds minimal complexity and is both RAG-agnostic and generally useful.

- **Ship RAG client libraries in the `gen-ai-rag` backend image** (`weaviate-client`, `neo4j`) so downstream RAG consumers don't pay a startup pip-install cost.

- **Add an `api_base` column to `public.llms`** to express custom-endpoint models natively in the catalog. Alternatively, document the `/model/new` pattern prominently as the standard way to register custom OpenAI-compatible endpoints.

- **Add a `--extra-compose <file>` flag to `start.sh`** so consumers can add overlays without symlinking into the gitignored `_user/` slot.

## Open items (pending live end-to-end run)

**Quality of local-first LightRAG extraction and agentic tool-calling:**
- LightRAG extraction using `gemma4:31b`
- Qwen v3.6 agentic tool-calling

These will be assessed after the full stack is brought up on a local machine. Placeholder marked intentionally open, not a silent gap.
