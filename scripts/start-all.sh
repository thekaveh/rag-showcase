#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

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
BP="$(grep -E '^BACKEND_PORT=' infra/.env | cut -d= -f2 || true)"
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
PROJECT_NAME="$(grep -E '^PROJECT_NAME=' infra/.env | cut -d= -f2 || true)"
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

OWUI="$(grep -E '^OPEN_WEB_UI_PORT=' infra/.env | cut -d= -f2 || true)"
[ -n "$OWUI" ] || { echo "OPEN_WEB_UI_PORT not found in infra/.env; aborting."; exit 1; }
echo "==> Ready. Open OpenWebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
