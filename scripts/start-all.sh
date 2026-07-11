#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

ATLAS_CONSUMER_MANIFEST="${ATLAS_CONSUMER_MANIFEST:-$ROOT/atlas.consumer.yml}"
ATLAS_CONSUMER_MANIFEST="$(python3 -c 'import os,sys; print(os.path.abspath(os.path.expanduser(sys.argv[1])))' "$ATLAS_CONSUMER_MANIFEST")"
export ATLAS_CONSUMER_MANIFEST

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
# Atlas subcommands do not apply consumer env overrides themselves. The
# preflight materializes a temporary active env from the manifest before each
# validation command; detached startup remains authoritative after source flags.
[ -f infra/.env ] || cp infra/.env.example infra/.env
uv run --project "$ROOT/infra/bootstrapper" python scripts/atlas_preflight.py

echo "==> Starting Atlas (gen-ai-rag track)…"
# doc-processor disabled: Atlas ships only GPU-container or localhost Docling, so
# there's no CPU-container option. ingest falls back to naive text chunking, so
# the .md/.txt corpus works with no GPU. For structure-aware chunking, switch to
# --doc-processor-source docling-localhost (run Docling on the host) or
# docling-container-gpu (needs an NVIDIA GPU).
# Atlas #503: the current dependency checker treats disabled Trino as enabled
# unless MinIO is available. Keep MinIO on until Atlas derives enablement from
# service manifests; remove this explicit source when that fix is pinned.
ATLAS_START_LOG="$(mktemp "${TMPDIR:-/tmp}/rag-showcase-atlas-start.XXXXXX")"
set +e
( cd infra && ./start.sh --consumer "$ATLAS_CONSUMER_MANIFEST" \
    --no-tui --detach --track gen-ai-rag \
    --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source disabled \
    --minio-source container ) 2>&1 | tee "$ATLAS_START_LOG"
ATLAS_START_STATUS=${PIPESTATUS[0]}
set -e
if [ "$ATLAS_START_STATUS" -ne 0 ]; then
  # Atlas #508: Compose can return nonzero when an expected one-shot exits 0,
  # before Atlas reaches its own detached status classifier. Accept only the
  # exact log signature and converged state; unrelated failures still abort.
  echo "==> Atlas detached start returned nonzero; checking the exited-zero fallback…"
  python3 scripts/verify_atlas_runtime.py --atlas-log "$ATLAS_START_LOG" || {
    rm -f "$ATLAS_START_LOG"
    echo "Atlas detached startup failed and the runtime did not converge." >&2
    exit 1
  }
fi
rm -f "$ATLAS_START_LOG"

PROJECT_NAME="$(envval PROJECT_NAME)"
[ -n "$PROJECT_NAME" ] || { echo "PROJECT_NAME not found in infra/.env; aborting."; exit 1; }

# Probe n8n /healthz from inside the backend after the wrapper-owned restart.
wait_for_n8n() {
  local ready=0
  for _ in $(seq 1 60); do
    if docker exec "${PROJECT_NAME}-backend" python -c \
         "import httpx,sys; sys.exit(0 if httpx.get('http://n8n:5678/healthz',timeout=5).status_code < 500 else 1)" \
         >/dev/null 2>&1; then ready=1; break; fi
    sleep 5
  done
  [ "$ready" = 1 ]
}

echo "==> Importing and activating the n8n adaptive-rag workflow…"
docker exec "${PROJECT_NAME}-n8n" \
  n8n import:workflow --input=/showcase-n8n/adaptive-rag.workflow.json --activeState=fromJson
# n8n's CLI updates the database, but the long-running n8n process only registers
# production webhooks at startup. Restart it after import so /webhook/adaptive-rag
# is live before the n8n-adaptive-rag plugin route is used.
docker restart "${PROJECT_NAME}-n8n" >/dev/null
wait_for_n8n || { echo "n8n did not become healthy after workflow import restart."; exit 1; }

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

if [ "${RAG_SHOWCASE_SKIP_DEFAULT_INGEST:-0}" != "1" ]; then
  echo "==> Ingesting corpus inside the backend container…"
  docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" \
    python /app/ingest/ingest.py /app/corpus/raw
fi

echo "==> Registering RAG models and flavor aliases in LiteLLM (inside the backend container)…"
# Run in-container: LiteLLM is reachable at http://litellm:4000 there, the key
# is present (LITELLM_API_KEY), and httpx is installed by the plugin seam. This
# also avoids shell-sourcing Atlas's .env (which has unquoted values).
docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" \
  python /app/register/register_models.py

echo "==> Verifying the six LiteLLM model routes are available…"
routes_ready=0
for _ in $(seq 1 30); do
  # -i is load-bearing: without it docker exec does not forward the heredoc on
  # stdin, `python -` reads EOF, runs an EMPTY program, and exits 0 — turning this
  # whole verification gate into a no-op that always passes on the first try.
  if docker exec -i -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" python - <<'PY' >/dev/null 2>&1
import os
import sys
import httpx

required = {
    "vanilla-rag",
    "hybrid-rag",
    "contextual-rag",
    "graph-rag",
    "agentic-rag",
    "n8n-adaptive-rag",
}
headers = {"Authorization": f"Bearer {os.environ.get('LITELLM_API_KEY', '')}"}
r = httpx.get("http://litellm:4000/v1/models", headers=headers, timeout=10)
r.raise_for_status()
found = {item.get("id") for item in r.json().get("data", [])}
sys.exit(0 if required <= found else 1)
PY
  then routes_ready=1; break; fi
  docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" \
    python /app/register/register_models.py >/dev/null 2>&1 || true
  sleep 2
done
[ "$routes_ready" = 1 ] || { echo "LiteLLM did not expose all six RAG model routes after registration."; exit 1; }

OWUI="$(envval OPEN_WEB_UI_PORT)"
[ -n "$OWUI" ] || { echo "OPEN_WEB_UI_PORT not found in infra/.env; aborting."; exit 1; }
echo "==> Ready. Open the Open WebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
