#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ATLAS_CONSUMER_MANIFEST="${ATLAS_CONSUMER_MANIFEST:-$ROOT/atlas.consumer.yml}"
ATLAS_CONSUMER_MANIFEST="$(python3 -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$ATLAS_CONSUMER_MANIFEST")"
export ATLAS_CONSUMER_MANIFEST

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

# Older releases linked this overlay into Atlas's ignored services/_user slot.
# Remove only that exact generated symlink so an upgraded checkout cannot load
# the same Compose fragment both there and through atlas.consumer.yml.
LEGACY_OVERLAY="$ROOT/infra/services/_user/rag-showcase/compose.yml"
if [ -L "$LEGACY_OVERLAY" ]; then
  [ "$(readlink "$LEGACY_OVERLAY")" = "../../../../compose/rag-overlay.yml" ] || {
    echo "Unexpected legacy overlay symlink at $LEGACY_OVERLAY; remove it manually." >&2
    exit 1
  }
  rm "$LEGACY_OVERLAY"
  rmdir "$(dirname "$LEGACY_OVERLAY")" 2>/dev/null || true
  rmdir "$ROOT/infra/services/_user" 2>/dev/null || true
elif [ -e "$LEGACY_OVERLAY" ]; then
  echo "Refusing to replace non-symlink legacy overlay: $LEGACY_OVERLAY" >&2
  exit 1
fi

# Read a key's value from Atlas's infra/.env. Atlas's .env can carry a key more
# than once (overlays/appends); dotenv and Compose both take the last assignment,
# so we do too (tail -1). This also keeps the result a single line even when the
# key is duplicated, so `docker exec "${PROJECT_NAME}-backend"` can't receive a
# multi-line container name. -f2- (not -f2): values may themselves contain '='.
envval() { grep -E "^$1=" infra/.env | tail -1 | cut -d= -f2- || true; }

echo "==> Running Atlas consumer-manifest preflight…"
[ -f infra/.env ] || cp infra/.env.example infra/.env
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" env backfill )
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" compose validate )
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" doctor --format json )

echo "==> Starting Atlas (gen-ai-rag track)…"
# doc-processor disabled: Atlas ships only GPU-container or localhost Docling, so
# there's no CPU-container option. ingest falls back to naive text chunking, so
# the .md/.txt corpus works with no GPU. For structure-aware chunking, switch to
# --doc-processor-source docling-localhost (run Docling on the host) or
# docling-container-gpu (needs an NVIDIA GPU).
ATLAS_START_LOG="$(mktemp "${TMPDIR:-/tmp}/rag-showcase-atlas-start.XXXXXX")"
set +e
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" \
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

# Atlas's generated file is authoritative for both the alias inventory and
# routes. Reconcile exact legacy DB duplicates on every start, then verify the
# owned rows and /v1/models discovery. This preserves all unrelated models and
# also handles a restored database independently of host-side marker state.
echo "==> Reconciling Atlas-declared LiteLLM model aliases…"
ALIAS_CHANGE_FILE="$(mktemp "${TMPDIR:-/tmp}/rag-showcase-aliases.XXXXXX")"
LITELLM_BASE_URL="http://127.0.0.1:$(envval LITELLM_PORT)" \
LITELLM_MASTER_KEY="$(envval LITELLM_MASTER_KEY)" \
  uv run python scripts/reconcile_litellm_aliases.py \
    --models-file infra/volumes/litellm/consumer-models.yaml \
    --changed-file "$ALIAS_CHANGE_FILE"
if [ "$(cat "$ALIAS_CHANGE_FILE")" -gt 0 ]; then
  # LiteLLM runs four workers. /model/delete removes the DB row, but sibling
  # workers retain their startup cache until the proxy restarts. Reload once so
  # this upgraded run cannot route to an obsolete pre-/rag deployment.
  echo "==> Reloading LiteLLM after legacy alias cleanup…"
  docker restart "${PROJECT_NAME}-litellm" >/dev/null
  litellm_ready=0
  for _ in $(seq 1 60); do
    if docker exec "${PROJECT_NAME}-backend" python -c \
         "import httpx,sys; sys.exit(0 if httpx.get('http://litellm:4000/health/liveliness',timeout=5).status_code == 200 else 1)" \
         >/dev/null 2>&1; then litellm_ready=1; break; fi
    sleep 2
  done
  [ "$litellm_ready" = 1 ] || { rm -f "$ALIAS_CHANGE_FILE"; echo "LiteLLM did not recover after alias cleanup."; exit 1; }
  LITELLM_BASE_URL="http://127.0.0.1:$(envval LITELLM_PORT)" \
  LITELLM_MASTER_KEY="$(envval LITELLM_MASTER_KEY)" \
    uv run python scripts/reconcile_litellm_aliases.py \
      --models-file infra/volumes/litellm/consumer-models.yaml \
      --changed-file "$ALIAS_CHANGE_FILE"
  [ "$(cat "$ALIAS_CHANGE_FILE")" -eq 0 ] || {
    rm -f "$ALIAS_CHANGE_FILE"
    echo "Legacy LiteLLM aliases remained after proxy reload." >&2
    exit 1
  }
fi
rm -f "$ALIAS_CHANGE_FILE"

# Atlas owns workflow import/update. n8n CE can activate the seeded workflow on
# the running process only when an operator-issued N8N_API_KEY is configured;
# otherwise Atlas persists it and explicitly requires one reload. Also remove
# the exact unnamespaced id owned by releases before consumer workflow seeding.
n8n_reload=0
if docker exec "${PROJECT_NAME}-n8n" n8n list:workflow 2>/dev/null \
     | grep -q '^adaptiverag00001|'; then
  echo "==> Removing the legacy unnamespaced adaptive-rag workflow…"
  docker exec -i -w /usr/local/lib/node_modules/n8n "${PROJECT_NAME}-n8n" \
    node - < "$ROOT/scripts/remove_legacy_n8n_workflow.js"
  n8n_reload=1
fi
if [ -z "$(envval N8N_API_KEY)" ]; then
  # Atlas can call n8n's activation API when a UI-issued key exists. Without
  # one, n8n 2.28 imports the normalized JSON as inactive despite active:true;
  # publish the Atlas-owned id through n8n's CLI, then reload as the CLI asks.
  echo "==> Publishing the Atlas-seeded adaptive-rag workflow…"
  docker exec "${PROJECT_NAME}-n8n" \
    n8n publish:workflow --id=atlas-consumer-adaptive-rag >/dev/null
  n8n_reload=1
fi
if [ "$n8n_reload" -eq 1 ]; then
  echo "==> Reloading n8n to activate the Atlas-seeded workflow…"
  docker restart "${PROJECT_NAME}-n8n" >/dev/null
  n8n_ready=0
  for _ in $(seq 1 60); do
    if docker exec "${PROJECT_NAME}-backend" python -c \
         "import httpx,sys; sys.exit(0 if httpx.get('http://n8n:5678/healthz',timeout=5).status_code < 500 else 1)" \
         >/dev/null 2>&1; then n8n_ready=1; break; fi
    sleep 5
  done
  [ "$n8n_ready" = 1 ] || { echo "n8n did not recover after workflow activation reload."; exit 1; }
fi

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

# Atlas's detached health gates do NOT guarantee Ollama has finished pulling
# the embed + chat models (a cold first run downloads several GB), and ingest's
# first embed/contextualize call would then 4xx/5xx and abort the run. Probe a
# real embed + chat round-trip through LiteLLM (using the plugin's own client and
# roles) before ingesting. Generous timeout: the chat model can be large.
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

echo "==> Verifying the Atlas-seeded adaptive-rag production webhook…"
docker exec -i "${PROJECT_NAME}-backend" python - <<'PY'
import os
import sys

import httpx

url = os.environ.get("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
response = httpx.post(
    url,
    json={"query": "What is retrieval-augmented generation?"},
    timeout=240,
)
response.raise_for_status()
sys.exit(0 if response.json().get("answer") else 1)
PY

if [ "${RAG_SHOWCASE_SKIP_DEFAULT_INGEST:-0}" != "1" ]; then
  echo "==> Running Atlas RAG ingestion profile ${RAG_INGESTION_PROFILE}…"
  uv run python -m ingest.atlas_job \
    --profile "$RAG_INGESTION_PROFILE" \
    --base-url "http://127.0.0.1:$(envval BACKEND_PORT)"
  echo "==> Building the showcase contextual index from Atlas-ingested chunks…"
  docker exec -e PYTHONPATH=/app/plugins:/app "${PROJECT_NAME}-backend" \
    python -m ingest.contextual
fi

OWUI="$(envval OPEN_WEB_UI_PORT)"
[ -n "$OWUI" ] || { echo "OPEN_WEB_UI_PORT not found in infra/.env; aborting."; exit 1; }
echo "==> Ready. Open the Open WebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
