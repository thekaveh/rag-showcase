#!/usr/bin/env bash
# Symlink the showcase's compose overlay into Atlas's _user overlay slot,
# so Atlas's bootstrapper auto-discovers and merges it. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT="$ROOT/infra/services/_user/rag-showcase"
mkdir -p "$SLOT"
ln -sf "../../../../compose/rag-overlay.yml" "$SLOT/compose.yml"
echo "Linked $SLOT/compose.yml -> compose/rag-overlay.yml"
