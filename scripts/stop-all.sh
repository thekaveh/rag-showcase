#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PROJECT_NAME="${RAG_SHOWCASE_PROJECT_NAME:-rag-showcase}"
ATLAS_CONSUMER_MANIFEST="${ATLAS_CONSUMER_MANIFEST:-$ROOT/atlas.consumer.yml}"
COLD=0
case "${1:-}" in
  "") ;;
  --cold) COLD=1 ;;
  *) echo "Usage: $0 [--cold]" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || { echo "Usage: $0 [--cold]" >&2; exit 2; }

stop_args=(--project "$PROJECT_NAME")
[ "$COLD" -eq 0 ] || stop_args+=(--cold)

# Atlas project-scoped teardown is ownership-aware; host-global runtime
# shutdown is intentionally omitted because those runtimes may be shared.
( cd "$ROOT/infra" && ATLAS_CONSUMER_MANIFEST="$ATLAS_CONSUMER_MANIFEST" \
    ./stop.sh --project "$PROJECT_NAME" "${stop_args[@]:2}" )

if docker ps -a --filter "label=com.docker.compose.project=$PROJECT_NAME" -q \
    | grep -q .; then
  echo "$PROJECT_NAME containers remain after Compose teardown." >&2
  exit 1
fi

echo "Verified that no $PROJECT_NAME containers remain."
