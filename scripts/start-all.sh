#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

./scripts/setup-overlay.sh

echo "==> Starting Atlas (gen-ai-rag track)…"
( cd infra && ./start.sh --track gen-ai-rag --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source docling-container-cpu )

echo "==> Waiting for the backend to report healthy…"
BP="$(grep -E '^BACKEND_PORT=' infra/.env | cut -d= -f2 || true)"
[ -n "$BP" ] || { echo "BACKEND_PORT not found in infra/.env; aborting."; exit 1; }
healthy=0
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${BP}/health" >/dev/null 2>&1; then healthy=1; break; fi
  sleep 5
done
[ "$healthy" = 1 ] || { echo "Backend did not become healthy after 5 minutes; aborting before ingest."; exit 1; }

echo "==> Ingesting corpus (inside the backend container)…"
python corpus/fetch_corpus.py
PROJECT_NAME="$(grep -E '^PROJECT_NAME=' infra/.env | cut -d= -f2 || true)"
[ -n "$PROJECT_NAME" ] || { echo "PROJECT_NAME not found in infra/.env; aborting."; exit 1; }
docker exec -e PYTHONPATH=/app/plugins "${PROJECT_NAME}-backend" \
  python /app/ingest/ingest.py /app/corpus/raw

echo "==> Registering the six models in LiteLLM…"
set -a; source infra/.env; set +a
python register/register_models.py

OWUI="$(grep -E '^OPEN_WEB_UI_PORT=' infra/.env | cut -d= -f2)"
echo "==> Ready. Open OpenWebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
