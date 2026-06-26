#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

# Read a key's value from Atlas's infra/.env. Atlas's .env can carry a key more
# than once (overlays/appends); dotenv and Compose both take the last assignment,
# so we do too (tail -1). This also keeps the result a single line even when the
# key is duplicated, so `docker exec "${PROJECT_NAME}-backend"` can't receive a
# multi-line container name.
envval() { grep -E "^$1=" infra/.env | tail -1 | cut -d= -f2 || true; }

./scripts/setup-overlay.sh

echo "==> Starting Atlas (gen-ai-rag track)…"
# doc-processor disabled: Atlas ships only GPU-container or localhost Docling, so
# there's no CPU-container option. ingest falls back to naive text chunking, so
# the .md/.txt corpus works with no GPU. For structure-aware chunking, switch to
# --doc-processor-source docling-localhost (run Docling on the host) or
# docling-container-gpu (needs an NVIDIA GPU).
# --n8n-source container: n8n isn't part of the gen-ai-rag track, but
# n8n-adaptive-rag needs it; request it explicitly so Atlas doesn't force-disable
# it on the non-interactive launch path.
( cd infra && ./start.sh --track gen-ai-rag --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source disabled \
    --n8n-source container )

echo "==> Waiting for the backend to report healthy…"
BP="$(envval BACKEND_PORT)"
[ -n "$BP" ] || { echo "BACKEND_PORT not found in infra/.env; aborting."; exit 1; }
healthy=0
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${BP}/health" >/dev/null 2>&1; then healthy=1; break; fi
  sleep 5
done
[ "$healthy" = 1 ] || { echo "Backend did not become healthy after 5 minutes; aborting before ingest."; exit 1; }

PROJECT_NAME="$(envval PROJECT_NAME)"
[ -n "$PROJECT_NAME" ] || { echo "PROJECT_NAME not found in infra/.env; aborting."; exit 1; }

# The backend healthcheck does NOT depend on LightRAG, and LightRAG (graph
# extraction) often comes up slower; without this gate, ingest's first upload
# could fail mid-run and leave graph-rag empty. Probe LightRAG /health over the
# in-network address ingest itself uses.
echo "==> Waiting for LightRAG to report healthy (graph-rag ingest needs it)…"
lr_ready=0
for _ in $(seq 1 60); do
  if docker exec "${PROJECT_NAME}-backend" python -c \
       "import httpx,sys; sys.exit(0 if httpx.get('http://lightrag:9621/health',timeout=5).status_code==200 else 1)" \
       >/dev/null 2>&1; then lr_ready=1; break; fi
  sleep 5
done
[ "$lr_ready" = 1 ] || { echo "LightRAG did not become healthy after 5 minutes; aborting before ingest (graph-rag would be empty)."; exit 1; }

# Ingest's first operation is vectors.ensure_collection (a Weaviate connect with
# no retry), and the backend healthcheck does not depend on Weaviate being ready.
# Gate on Weaviate's readiness endpoint before ingest, mirroring the LightRAG gate.
echo "==> Waiting for Weaviate to report ready (ingest creates collections first)…"
wv_ready=0
for _ in $(seq 1 60); do
  if docker exec "${PROJECT_NAME}-backend" python -c \
       "import httpx,sys; sys.exit(0 if httpx.get('http://weaviate:8080/v1/.well-known/ready',timeout=5).status_code==200 else 1)" \
       >/dev/null 2>&1; then wv_ready=1; break; fi
  sleep 5
done
[ "$wv_ready" = 1 ] || { echo "Weaviate did not become ready after 5 minutes; aborting before ingest."; exit 1; }

echo "==> Assembling corpus on the host (corpus/raw/)…"
# host python3 on purpose: fetch_corpus is stdlib-only, and using the host
# interpreter (not the uv env, which omits `datasets`) lets an optional host-side
# `python3 -m pip install datasets` take effect. python3, not bare `python`, for
# portability (stock macOS — the documented platform — ships only python3).
python3 corpus/fetch_corpus.py

# The backend/LightRAG health gates do NOT guarantee Ollama has finished pulling
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

echo "==> Ingesting corpus inside the backend container…"
docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" \
  python /app/ingest/ingest.py /app/corpus/raw

echo "==> Registering the six models in LiteLLM (inside the backend container)…"
# Run in-container: LiteLLM is reachable at http://litellm:4000 there, the key
# is present (LITELLM_API_KEY), and httpx is installed by the plugin seam. This
# also avoids shell-sourcing Atlas's .env (which has unquoted values).
docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" \
  python /app/register/register_models.py

OWUI="$(envval OPEN_WEB_UI_PORT)"
[ -n "$OWUI" ] || { echo "OPEN_WEB_UI_PORT not found in infra/.env; aborting."; exit 1; }
echo "==> Ready. Open OpenWebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
