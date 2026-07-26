#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

PROJECT_NAME="${RAG_SHOWCASE_PROJECT_NAME:-rag-showcase}"
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
# Pass the whole stop_args array once (it already begins with --project <name>);
# the earlier `${stop_args[@]:2}` slice re-derived the same tail but hard-coded
# the assumption that indices 0,1 were `--project <name>`, silently dropping any
# flag a future maintainer prepended.
( cd "$ROOT/infra" && ./stop.sh "${stop_args[@]}" )

if docker ps -a --filter "label=com.docker.compose.project=$PROJECT_NAME" -q \
    | grep -q .; then
  echo "$PROJECT_NAME containers remain after Compose teardown." >&2
  exit 1
fi

echo "Verified that no $PROJECT_NAME containers remain."
