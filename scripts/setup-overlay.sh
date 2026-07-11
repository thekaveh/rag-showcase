#!/usr/bin/env bash
# Prepare the vendored Atlas stack for the showcase by linking the Compose
# overlay into Atlas's backward-compatible _user slot. Issue #18 will replace
# this final symlink with Atlas's consumer manifest.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT="$ROOT/infra/services/_user/rag-showcase"
ENV_USER_FILE="${ATLAS_ENV_USER_FILE:-$ROOT/config/atlas.env.user}"

[ -r "$ENV_USER_FILE" ] || {
  echo "Atlas env overlay is missing or unreadable: $ENV_USER_FILE" >&2
  exit 1
}

# Atlas merges every services/_user/*/compose.yml after its generated graph.
mkdir -p "$SLOT"
ln -sf "../../../../compose/rag-overlay.yml" "$SLOT/compose.yml"
echo "Linked $SLOT/compose.yml -> compose/rag-overlay.yml"
echo "Using parent-owned Atlas env overlay: $ENV_USER_FILE"
