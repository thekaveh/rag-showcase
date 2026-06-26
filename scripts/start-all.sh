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
( cd infra && ./start.sh --track gen-ai-rag --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source disabled )

echo "==> Waiting for the backend to report healthy…"
BP="$(envval BACKEND_PORT)"
[ -n "$BP" ] || { echo "BACKEND_PORT not found in infra/.env; aborting."; exit 1; }
healthy=0
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${BP}/health" >/dev/null 2>&1; then healthy=1; break; fi
  sleep 5
done
[ "$healthy" = 1 ] || { echo "Backend did not become healthy after 5 minutes; aborting before ingest."; exit 1; }

echo "==> Assembling corpus on the host (corpus/raw/)…"
# bare python on purpose: fetch_corpus is stdlib-only, and bare python lets an
# optional host-side `pip install datasets` take effect (the uv env omits it).
python corpus/fetch_corpus.py
PROJECT_NAME="$(envval PROJECT_NAME)"
[ -n "$PROJECT_NAME" ] || { echo "PROJECT_NAME not found in infra/.env; aborting."; exit 1; }
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
