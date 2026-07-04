# Atlas LightRAG Alignment Design

Date: 2026-07-02
Status: Historical design artifact — implemented; the code is authoritative.
Deviation from §5's acceptance criteria: a minimal `services.lightrag` section
with optional `*_OLLAMA_LLM_NUM_CTX` caps was re-added to the overlay after the
alignment (commit 15c1c8d) because Atlas exposes no public input for them.

## 1. Goal

Align rag-showcase with the updated Atlas LightRAG and RAG-track contracts while keeping this repo hardware-neutral.

## 2. Context

Atlas now exposes LightRAG role-specific model inputs as first-class `.env` variables:

- `LIGHTRAG_EXTRACT_LLM_MODEL`
- `LIGHTRAG_KEYWORD_LLM_MODEL`
- `LIGHTRAG_QUERY_LLM_MODEL`
- matching role binding, binding host, API key, concurrency, and timeout inputs

Atlas also now owns LightRAG query defaults for rerank and fanout:

- `LIGHTRAG_QUERY_ENABLE_RERANK=false`
- `LIGHTRAG_QUERY_TOP_K=10`
- `LIGHTRAG_QUERY_CHUNK_TOP_K=5`
- `LIGHTRAG_QUERY_MAX_TOTAL_TOKENS=12000`

Finally, Atlas now supports `LLM_PROVIDER_SOURCE=ollama-localhost`, but rag-showcase must not assume any particular host hardware. The default path should work through Atlas and LiteLLM regardless of whether the active model backend is container CPU, container GPU, host Ollama, or another supported provider.

## 3. Design

Rag-showcase will stop setting LightRAG's native runtime variables directly in its compose overlay. Instead, it will configure Atlas's public `.env` inputs during `scripts/setup-overlay.sh`, then let Atlas render those inputs into the LightRAG service.

The compose overlay remains responsible only for rag-showcase-specific integration:

- mounting `backend_plugins`, `ingest`, `corpus`, and `register` into the Atlas backend;
- setting plugin-specific env such as `BACKEND_PLUGINS_DIR`, `RAG_ROLES_FILE`, and `RAG_MODELS_FILE`;
- passing graph query request defaults to the backend plugin, because Atlas's backend container does not currently inject those query-tuning variables.

The setup script will set default LightRAG role model choices only when the corresponding Atlas variables are absent or empty. This keeps the default comparison reproducible while allowing users to override models, providers, and hardware paths in `infra/.env`.

## 4. Hardware Neutrality

The repo will not describe the default architecture as Mac-specific or host-Ollama-specific. Documentation may mention host Ollama as one supported Atlas source option, but it must not be presented as a requirement.

The default LightRAG role model remains configurable. If the default Ollama model is used, `scripts/setup-overlay.sh` adds it to `OLLAMA_CUSTOM_MODELS` so Atlas can register/pull it for container Ollama sources. Host-Ollama users remain responsible for pulling models on the host, matching Atlas's `ollama-localhost` contract.

## 5. Acceptance Criteria

- `infra/` submodule points at the latest Atlas `main` containing LightRAG role support.
- `compose/rag-overlay.yml` no longer sets `lightrag` / `lightrag-init` runtime overrides.
- `scripts/setup-overlay.sh` writes Atlas-prefixed LightRAG defaults only when unset.
- Tests assert the overlay no longer bypasses Atlas's LightRAG contract.
- README and comparison docs describe Atlas-owned LightRAG role/query support as current behavior.
- GitHub repository About text is hardware-neutral.
