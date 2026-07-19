#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ATLAS_CONSUMER_MANIFEST="${ATLAS_CONSUMER_MANIFEST:-$ROOT/atlas.consumer.yml}"
ATLAS_CONSUMER_MANIFEST="$(python3 -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$ATLAS_CONSUMER_MANIFEST")"
export ATLAS_CONSUMER_MANIFEST

ATLAS_PROJECT_NAME="${RAG_SHOWCASE_PROJECT_NAME:-rag-showcase}"
# Atlas's native `--base-port auto` selects the first wholly-free BASE_PORT block
# (using Atlas's own topology span, below the ephemeral range) and persists it to
# infra/.env — no consumer-side finder or launch lock. Pin RAG_SHOWCASE_BASE_PORT
# to force a specific block instead.
ATLAS_BASE_PORT="${RAG_SHOWCASE_BASE_PORT:-auto}"

# Provider sources belong to Atlas. Omit them by default so a consumer can use
# its existing Atlas configuration without this repository assuming host hardware.
ATLAS_SOURCE_ARGS=()
if [ -n "${RAG_SHOWCASE_LLM_PROVIDER_SOURCE:-}" ]; then
  ATLAS_SOURCE_ARGS+=(--llm-provider-source "$RAG_SHOWCASE_LLM_PROVIDER_SOURCE")
fi
if [ -n "${RAG_SHOWCASE_COMFYUI_SOURCE:-}" ]; then
  ATLAS_SOURCE_ARGS+=(--comfyui-source "$RAG_SHOWCASE_COMFYUI_SOURCE")
fi

RAG_INGESTION_PROFILE="${RAG_INGESTION_PROFILE:-showcase_default}"
case "$RAG_INGESTION_PROFILE" in
  ""|*[!a-z0-9._-]*|[._-]*)
    echo "Invalid RAG_INGESTION_PROFILE: $RAG_INGESTION_PROFILE" >&2
    exit 1
    ;;
esac
RAG_BASE_COLLECTION="${RAG_BASE_COLLECTION:-RagBase_${RAG_INGESTION_PROFILE}}"
RAG_CONTEXTUAL_COLLECTION="${RAG_CONTEXTUAL_COLLECTION:-RagContextual_${RAG_INGESTION_PROFILE}}"
export RAG_INGESTION_PROFILE RAG_BASE_COLLECTION RAG_CONTEXTUAL_COLLECTION

# Read a key's value from Atlas's infra/.env. Atlas's .env can carry a key more
# than once (overlays/appends); dotenv and Compose both take the last assignment,
# so we do too (tail -1). This also keeps the result a single line even when the
# key is duplicated, so `docker exec "${PROJECT_NAME}-backend"` can't receive a
# multi-line container name. -f2- (not -f2): values may themselves contain '='.
envval() { grep -E "^$1=" infra/.env | tail -1 | cut -d= -f2- || true; }

# LightRAG KEYWORD/QUERY role keys need no consumer wiring: Atlas defaults them to
# ${LITELLM_MASTER_KEY} when the LIGHTRAG_* override is unset (atlas #721), so the
# in-network LiteLLM bindings authenticate without us mutating Atlas's infra/.env.

echo "==> Running Atlas consumer-manifest preflight…"
[ -f infra/.env ] || cp infra/.env.example infra/.env
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" \
    --project "$ATLAS_PROJECT_NAME" --base-port "$ATLAS_BASE_PORT" \
    "${ATLAS_SOURCE_ARGS[@]}" env backfill )
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" \
    --project "$ATLAS_PROJECT_NAME" --base-port "$ATLAS_BASE_PORT" \
    "${ATLAS_SOURCE_ARGS[@]}" compose validate )
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" \
    --project "$ATLAS_PROJECT_NAME" --base-port "$ATLAS_BASE_PORT" \
    "${ATLAS_SOURCE_ARGS[@]}" doctor --format json )

echo "==> Starting Atlas (gen-ai-rag track)…"
# doc-processor disabled: Atlas ships only GPU-container or localhost Docling, so
# there's no CPU-container option. ingest falls back to naive text chunking, so
# the .md/.txt corpus works with no GPU. For structure-aware chunking, switch to
# --doc-processor-source docling-localhost (run Docling on the host) or
# docling-container-gpu (needs an NVIDIA GPU).
ATLAS_START_LOG="$(mktemp "${TMPDIR:-/tmp}/rag-showcase-atlas-start.XXXXXX")"
set +e
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" \
    --project "$ATLAS_PROJECT_NAME" --base-port "$ATLAS_BASE_PORT" \
    "${ATLAS_SOURCE_ARGS[@]}" \
    --no-tui --detach --track gen-ai-rag \
    --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source disabled ) \
    2>&1 | tee "$ATLAS_START_LOG"
ATLAS_START_STATUS=${PIPESTATUS[0]}
set -e
if [ "$ATLAS_START_STATUS" -ne 0 ]; then
  # Atlas #508 recognizes only an already-converged snapshot. Compose can
  # report an exited-zero one-shot while healthy services are still starting,
  # so wait only for that exact signature and reject every genuine failure.
  echo "==> Atlas returned during a successful one-shot race; checking convergence…"
  python3 scripts/verify_atlas_runtime.py --atlas-log "$ATLAS_START_LOG" || {
    rm -f "$ATLAS_START_LOG"
    echo "Atlas detached startup failed and the runtime did not converge." >&2
    exit 1
  }
fi
rm -f "$ATLAS_START_LOG"

PROJECT_NAME="$(envval PROJECT_NAME)"
[ -n "$PROJECT_NAME" ] || { echo "PROJECT_NAME not found in infra/.env; aborting."; exit 1; }

# Atlas compiles the consumer-declared LiteLLM aliases (`litellm_models` in
# atlas.consumer.yml) into config.yaml before the proxy starts, so every alias is
# discoverable in /v1/models at boot without any consumer-side admin-API mutation
# or `docker restart`. The old per-start reconcile deleted rows from a retired
# registration script (now gone), which is why it needed to flush worker caches.

# Atlas owns n8n workflow import + activation. With no N8N_API_KEY, Atlas's seed
# now persists active=true via `n8n publish:workflow` AND restarts n8n once
# post-seed (_reactivate_n8n_if_needed) to register the production webhook — so
# the consumer needs no manual publish:workflow or `docker restart` (atlas #720).

if [ "${RAG_SHOWCASE_SKIP_DEFAULT_INGEST:-0}" != "1" ]; then
  echo "==> Assembling corpus on the host (corpus/raw/)…"
  # host python3 on purpose: fetch_corpus is stdlib-only, and using the host
  # interpreter (not the uv env, which omits `datasets`) lets an optional host-side
  # `python3 -m pip install datasets` take effect. python3, not bare `python`, for
  # portability (stock macOS — the documented platform — ships only python3).
  python3 corpus/fetch_corpus.py
else
  echo "==> Skipping default corpus ingest (RAG_SHOWCASE_SKIP_DEFAULT_INGEST=1)…"
fi

# Read-only model-readiness diagnostic (#53): Atlas's detached health gates do NOT
# guarantee Ollama has finished pulling the embed + chat models (a cold first run
# downloads several GB), and ingest's first embed/contextualize call would then
# 4xx/5xx and abort the run. Probe a real embed + chat round-trip through LiteLLM
# (using the plugin's own client and roles) before ingesting — it mutates nothing.
# The only remaining docker exec targets are the consumer's OWN plugin/ingest code
# in the backend (the plugin seam's runtime); no exec/restart reaches an Atlas
# service (LiteLLM cache/#49, n8n activation/#51 are gone). Generous timeout.
echo "==> Waiting for the local models (embed + chat) to be pulled and serving…"
models_ready=0
for _ in $(seq 1 180); do
  if docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" python -c '
import asyncio
from rag.common import litellm, config
async def _probe():
    await litellm.embed(["ping"])
    await litellm.chat(config.role("contextual_blurb"), [{"role": "user", "content": "hi"}])
asyncio.run(_probe())
' >/dev/null 2>&1; then models_ready=1; break; fi
  sleep 10
done
[ "$models_ready" = 1 ] || { echo "Local models not ready after ~30 min; aborting before ingest."; exit 1; }

if [ "${RAG_SHOWCASE_SKIP_DEFAULT_INGEST:-0}" != "1" ]; then
  echo "==> Running Atlas RAG ingestion profile ${RAG_INGESTION_PROFILE}…"
  BACKEND_INTERNAL_API_TOKEN="$(envval BACKEND_INTERNAL_API_TOKEN)" \
    uv run python -m ingest.atlas_job \
    --profile "$RAG_INGESTION_PROFILE" \
    --base-url "http://127.0.0.1:$(envval BACKEND_PORT)"
  # Consumer-owned ingest step (#53): builds the showcase's contextual index from
  # the mounted /app/corpus + in-network Weaviate/LiteLLM, so it runs in the plugin
  # runtime (the backend). Atlas exposes no post-ingest hook to offload it, so this
  # stays an exec of our OWN code — not coupling to an Atlas service internal.
  echo "==> Building the showcase contextual index from Atlas-ingested chunks…"
  docker exec -e PYTHONPATH=/app/plugins:/app "${PROJECT_NAME}-backend" \
    python -m ingest.contextual
  echo "==> Verifying the Atlas-seeded adaptive-rag production webhook…"
  uv run python scripts/verify_adaptive_webhook.py \
    --url "http://127.0.0.1:$(envval N8N_PORT)/webhook/adaptive-rag"
else
  echo "==> Deferring adaptive-rag semantic verification until dataset ingestion…"
fi

OWUI="$(envval OPEN_WEB_UI_PORT)"
[ -n "$OWUI" ] || { echo "OPEN_WEB_UI_PORT not found in infra/.env; aborting."; exit 1; }
echo "==> Ready. Open the Open WebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag, lazy-graph-rag."
