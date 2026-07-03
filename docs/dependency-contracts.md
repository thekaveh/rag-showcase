# Consumed External-Dependency Contract Ledger

This showcase runs as a plugin on the vendored
[Atlas](https://github.com/thekaveh/atlas) stack (`infra/` submodule) and calls
several external systems as a client. This ledger records each consumed
integration point and the **exact pinned version** its contract was verified
against, so a future dependency bump surfaces as a reviewable diff instead of a
silent runtime break.

It is a point-in-time audit, not a live check. Re-verify after bumping the
`infra/` submodule or any pin below.

- **Audited:** 2026-07-03
- **Atlas submodule:** `8ce6784` (`v0.1.0-41-g8ce6784`)
- **Method:** contract fields read from the pinned image/source in `infra/` and
  the dependency's tagged source; no live stack required. The unit suite mocks
  these boundaries, so a green suite is **not** evidence of conformance.

## 1. Contract Ledger

| Integration point | Consumed by | Pinned version (source) | Contract verified | Status |
|---|---|---|---|---|
| Atlas bootstrapper `start.py` (click CLI) | `scripts/start-all.sh` | `infra/` @ `8ce6784` | Every flag start-all passes is an accepted `click.Choice`: `--track gen-ai-rag`, `--lightrag-source container`, `--tei-reranker-source container-cpu`, `--doc-processor-source disabled`, `--n8n-source container` (n8n is out-of-track for gen-ai-rag, hence passed explicitly) | conformant |
| LiteLLM admin + OpenAI API | `register/register_models.py`, `backend_plugins/rag/common/litellm.py` | `ghcr.io/berriai/litellm:v1.83.14-stable.patch.2` (`services/litellm/compose.yml`; `STORE_MODEL_IN_DB=True`) | `/model/new` body `{model_name, litellm_params, model_info}`; `/model/info` → `data[].model_info.id`; `/model/delete {id}`; `/v1/embeddings` → `data[].{embedding,index}`; `/v1/chat/completions` → `choices[0].message.{content,tool_calls}`; top-level `think` forwarded to Ollama | conformant |
| Weaviate v4 Python client | `backend_plugins/rag/common/vectors.py` | `weaviate-client>=4.9,<5` (`backend_plugins/requirements.txt`) | `connect_to_custom`; `collections.{exists,create,delete,get}`; `Configure.Vectorizer.none`; `query.near_vector`; `query.hybrid(..., return_metadata=MetadataQuery(score=True))`; `batch.dynamic()` + `failed_objects`; `o.metadata.score` / `o.properties` | conformant |
| LightRAG server HTTP API | `backend_plugins/rag/common/lightrag.py` | `ghcr.io/hkuds/lightrag:v1.5.4` (`services/lightrag/compose.yml`, `service.yml`) | `X-API-Key` auth (not `Authorization: Bearer`); `/query` `{mode, enable_rerank, top_k, chunk_top_k, max_total_tokens}` with `query` min_length 3; `/documents/text` `{text, file_source}`; 409-backpressure retries; response field `response`/`data`; modes `local`/`hybrid` | conformant |
| TEI reranker | `backend_plugins/rag/common/vectors.py` | `ghcr.io/huggingface/text-embeddings-inference:cpu-1.9` (`services/tei-reranker/compose.yml`; `--max-client-batch-size=32`) | `POST /rerank {query, texts}` → `[{index, score}]`; the plugin's `TEI_RERANKER_MAX_BATCH` default (32) matches the server's client-batch cap | conformant |
| n8n webhook + import CLI | `backend_plugins/rag/approaches/n8n.py`, `scripts/start-all.sh` | `n8nio/n8n:2.28.2` (`services/n8n`) | `POST /webhook/adaptive-rag {query}` → `{answer, route}`; `import:workflow --activeState=fromJson` (queue-mode only — Atlas runs n8n in queue mode); the workflow's classifier model `qwen3.6:latest` is Atlas-registered | conformant |
| `datasets` (Hugging Face) | `corpus/fetch_corpus.py` | optional import (not pinned) | `load_dataset("yixuantt/MultiHopRAG", "corpus", split="train")`; guarded `try/except` → keyword-docs-only fallback | conformant |
| Atlas Ollama model catalog | `backend_plugins/rag/roles.yaml`, `models.yaml` | `infra/` @ `8ce6784` (`services/ollama/models.yaml`) | Role models `qwen3.6:latest` (chat) and `nomic-embed-text` (embed) are `default_active` in Atlas's catalog | conformant |

## 2. Re-verification

After bumping `infra/` or any pin above, re-check each row against the new pinned
contract (image tag / submodule SHA / client version bound). Verify against the
pinned source, not the repo's own mocks. The most drift-prone rows are:

- **LightRAG** — field/header renames have occurred between minor versions
  (e.g. the `X-API-Key` vs `Authorization: Bearer` auth scheme, the
  `file_source` insert field). A mismatch surfaces as a 401/422 at runtime.
- **Atlas `start.py` flags** — a rejected `--*-source` `choice` aborts the whole
  bring-up before anything starts.
