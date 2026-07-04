# Consumed External-Dependency Contract Ledger

This showcase runs as a plugin on the vendored
[Atlas](https://github.com/thekaveh/atlas) stack (`infra/` submodule) and calls
several external systems as a client. This ledger records each consumed
integration point and the **exact pinned version** its contract was verified
against, so a future dependency bump surfaces as a reviewable diff instead of a
silent runtime break.

It is a point-in-time audit, not a live check. Re-verify after bumping the
`infra/` submodule or any pin below.

- **Audited:** 2026-07-04 (extends the 2026-07-03 audit; every prior row
  re-verified at the same pins)
- **Atlas submodule:** `8ce6784` (`v0.1.0-41-g8ce6784`); Atlas upstream `main`
  was 36 commits ahead at audit time with **byte-identical** values for every
  consumed image pin below (the lag is additive services, not contract-moving)
- **Method:** contract fields read from the pinned image/source in `infra/` and
  the dependency's tagged source; no live stack required. The unit suite mocks
  these boundaries, so a green suite is **not** evidence of conformance. Where a
  contract test pins a row (noted below), drift fails the suite.

## 1. Contract Ledger

| Integration point | Consumed by | Pinned version (source) | Contract verified | Status |
|---|---|---|---|---|
| Atlas bootstrapper `start.py` (click CLI) | `scripts/start-all.sh` | `infra/` @ `8ce6784` | `--track` is a `type=str` option validated against `tracks.yml` (`gen-ai-rag` is a defined track key); the four `--*-source` flags are `click.Choice` and every value start-all passes is accepted: `--lightrag-source container`, `--tei-reranker-source container-cpu`, `--doc-processor-source disabled`, `--n8n-source container` (n8n is out-of-track for gen-ai-rag, hence passed explicitly) | conformant |
| LiteLLM admin + OpenAI API | `register/register_models.py`, `backend_plugins/rag/common/litellm.py` | `ghcr.io/berriai/litellm:v1.83.14-stable.patch.2` (`services/litellm/compose.yml`; `STORE_MODEL_IN_DB=True`) | `/model/new` body `{model_name, litellm_params, model_info}`; `/model/info` → `data[].model_info.id`; `/model/delete {id}`; `/v1/embeddings` → `data[].{embedding,index}`; `/v1/chat/completions` → `choices[0].message.{content,tool_calls}`; top-level `think` forwarded to Ollama | conformant |
| Weaviate v4 Python client | `backend_plugins/rag/common/vectors.py` | `weaviate-client>=4.9,<5` (`backend_plugins/requirements.txt`) | `connect_to_custom`; `collections.{exists,create,delete,get}`; `Configure.Vectorizer.none`; `query.near_vector`; `query.hybrid(..., return_metadata=MetadataQuery(score=True))`; `batch.dynamic()` + `failed_objects`; `o.metadata.score` / `o.properties` | conformant |
| LightRAG server HTTP API | `backend_plugins/rag/common/lightrag.py` | `ghcr.io/hkuds/lightrag:v1.5.4` (`services/lightrag/compose.yml`, `service.yml`) | `X-API-Key` auth (not `Authorization: Bearer`); `/query` `{mode, enable_rerank, top_k, chunk_top_k, max_total_tokens}` with `query` min_length 3; `/documents/text` `{text, file_source}`; 409-backpressure retries; response field `response`/`data`; modes `local`/`hybrid` | conformant |
| TEI reranker | `backend_plugins/rag/common/vectors.py` | `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9` (`services/tei-reranker/compose.yml`; `--max-client-batch-size=32`) | `POST /rerank {query, texts}` → `[{index, score}]`; the plugin's `TEI_RERANKER_MAX_BATCH` default (32) matches the server's client-batch cap | conformant |
| n8n webhook + import CLI | `backend_plugins/rag/approaches/n8n.py`, `scripts/start-all.sh` | `n8nio/n8n:2.28.2` (`services/n8n`) | `POST /webhook/adaptive-rag {query}` → `{answer, route}`; `import:workflow --activeState=fromJson` (queue-mode only — Atlas runs n8n in queue mode); the workflow's classifier model `qwen3.6:latest` is Atlas-registered | conformant |
| `datasets` (Hugging Face) | `corpus/fetch_corpus.py` | optional import (not pinned) | `load_dataset("yixuantt/MultiHopRAG", "corpus", split="train")`; guarded `try/except` → keyword-docs-only fallback | conformant |
| Atlas Ollama model catalog | `backend_plugins/rag/roles.yaml`, `models.yaml` | `infra/` @ `8ce6784` (`services/ollama/models.yaml`) | Role models `qwen3.6:latest` (chat) and `nomic-embed-text` (embed) are `default_active` in Atlas's catalog | conformant |
| Atlas backend plugin seam | `backend_plugins/rag/__init__.py`, `backend_plugins/requirements.txt`, `compose/rag-overlay.yml` | `infra/` @ `8ce6784` (`services/backend/app/app/plugin_seam.py`, `main.py`) | Discovers immediate subdirs of `BACKEND_PLUGINS_DIR` (default `/app/plugins`) containing `__init__.py` that exposes a module-level `router`; pip-installs `<plugins_dir>/requirements.txt` at startup; the overlay's `../backend_plugins:/app/plugins:ro` mount + `BACKEND_PLUGINS_DIR` env match | conformant (route set pinned by `tests/../test_router.py`) |
| Atlas `_user` compose-overlay discovery | `scripts/setup-overlay.sh`, `compose/rag-overlay.yml` | `infra/` @ `8ce6784` (`bootstrapper/core/docker_manager.py`) | Sorted glob of `services/_user/*/compose.yml` merged after the base file with project dir `infra/`, so the overlay's `../<dir>` relative mounts resolve to this repo's root; the symlink target depth (`../../../../compose/rag-overlay.yml`) matches | conformant |
| LightRAG ops endpoints (beyond query/insert) | `scripts/run-dataset-ladder.py`, `scripts/start-all.sh` | `ghcr.io/hkuds/lightrag:v1.5.4` | `GET /documents/pipeline_status` → `{busy, request_pending, latest_message, docs, cur_batch, batchs}` (LightRAG's own field spelling); `GET /documents` → `{statuses}` (pending/processing/failed buckets, case-varying); `GET /health` | conformant (drain semantics pinned by ladder tests) |
| LiteLLM model listing | `scripts/start-all.sh` (six-route verification gate), `tests/test_demo_matrix.py` | `ghcr.io/berriai/litellm:v1.83.14-stable.patch.2` | `GET /v1/models` (Bearer auth) → `data[].id` | conformant |
| Weaviate server | `backend_plugins/rag/common/vectors.py` (via the v4 client), `scripts/start-all.sh` | `cr.weaviate.io/semitechnologies/weaviate:1.38.2` (`infra/.env.example` `WEAVIATE_IMAGE`) | HTTP 8080 + gRPC 50051; hybrid default fusion = relativeScoreFusion (≥1.24); readiness `GET /v1/.well-known/ready` | conformant |
| Docling document processor (opt-in) | `ingest/ingest.py` | Atlas `--doc-processor-source docling-localhost` / `docling-container-gpu` (disabled by default) | `POST {DOCLING_ENDPOINT}/v1/document/convert` multipart `file` + `{output_format, enable_chunking, chunk_size, chunk_overlap}` → `chunks[].{text, metadata.section_title}`; failures degrade to naive chunking for `.md`/`.txt`; PDFs are skipped loudly instead (naive chunking cannot parse binary) | conformant |
| Atlas `.env` key surface | `scripts/setup-overlay.sh`, `scripts/start-all.sh`, `compare/run_matrix.py`, `tests/conftest.py` | `infra/` @ `8ce6784` (`.env.example`) | Keys consumed: `PROJECT_NAME`, `BACKEND_PORT`, `OPEN_WEB_UI_PORT`, `LITELLM_PORT`, `LITELLM_MASTER_KEY`, `BRAND_{NAME,TAGLINE,REPO_URL,LOGO_FILE}`, `LIGHTRAG_{EMBEDDING,EXTRACT_LLM,KEYWORD_LLM,QUERY_LLM}_MODEL`, `LIGHTRAG_EXTRACT_MAX_ASYNC_LLM`, `LIGHTRAG_EXTRACT_LLM_TIMEOUT`, `OLLAMA_CUSTOM_MODELS` — all present in the pinned `.env.example`; duplicate keys resolve last-assignment-wins everywhere | conformant |
| MITRE ATT&CK STIX bundle (public) | `corpus/adapters/cyber_threat_intel.py` | unpinned public raw URL (`attack-stix-data` master, enterprise bundle) | STIX 2.1 `objects[].{type,id,name,description,external_references[].external_id,revoked,x_mitre_deprecated}`; relationship `{source_ref,target_ref,relationship_type}` | conformant |
| GDELT DOC 2.0 API (public) | `corpus/adapters/gdelt_events.py` | unpinned public API | `mode=artlist&format=json&maxrecords≤250&startdatetime/enddatetime` (YYYYMMDDHHMMSS) → `articles[].{url,title,domain,seendate,sourcecountry,language}`; 200-with-text error bodies handled | conformant |
| OpenAlex `/works` API (public) | `corpus/adapters/openalex_scholarly.py` | unpinned public API | `search`, `per-page≤200`, `sort=cited_by_count:desc`, `mailto` (polite pool) → `results[].{title,display_name,authorships,topics/concepts,abstract_inverted_index,referenced_works,primary_location.source,doi}` (`topics` preferred; `concepts` frozen upstream) | conformant |
| STaRK SKB loader (optional) | `corpus/adapters/stark_export.py` | `stark-qa` (host-installed, unpinned; guarded ImportError) | `load_skb(name, download_processed=True)`; `skb.node_info` / `skb.candidate_ids` | conformant |

## 2. Re-verification

After bumping `infra/` or any pin above, re-check each row against the new pinned
contract (image tag / submodule SHA / client version bound). Verify against the
pinned source, not the repo's own mocks. The most drift-prone rows are:

- **LightRAG** — field/header renames have occurred between minor versions
  (e.g. the `X-API-Key` vs `Authorization: Bearer` auth scheme, the
  `file_source` insert field). A mismatch surfaces as a 401/422 at runtime.
- **Atlas `start.py` flags** — a rejected `--*-source` `choice` aborts the whole
  bring-up before anything starts.
