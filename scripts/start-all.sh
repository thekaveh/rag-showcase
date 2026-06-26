#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

./scripts/setup-overlay.sh

echo "==> Starting Atlas (gen-ai-rag track)…"
( cd infra && ./start.sh --track gen-ai-rag --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source docling-container-cpu )

echo "==> Waiting for the backend to report healthy…"
BP="$(grep -E '^BACKEND_PORT=' infra/.env | cut -d= -f2)"
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${BP}/health" >/dev/null 2>&1; then break; fi
  sleep 5
done

echo "==> Ingesting corpus…"
python corpus/fetch_corpus.py
docker exec "$(grep -E '^PROJECT_NAME=' infra/.env | cut -d= -f2)-backend" \
  python /app/plugins/../ingest/ingest.py /app/plugins/../corpus/raw || \
  python ingest/ingest.py corpus/raw   # fallback: run from host if it can reach the stack

echo "==> Registering the six models in LiteLLM…"
set -a; source infra/.env; set +a
python register/register_models.py

OWUI="$(grep -E '^OPEN_WEB_UI_PORT=' infra/.env | cut -d= -f2)"
echo "==> Ready. Open OpenWebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
