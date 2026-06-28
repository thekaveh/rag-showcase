#!/usr/bin/env bash
# Prepare the vendored Atlas stack for the showcase: (1) symlink the compose
# overlay into Atlas's _user slot so the bootstrapper auto-discovers it, and
# (2) brand the stack as "rag-showcase" (project name + banner text + block-art
# logo). Both steps are idempotent and run on every start-all.sh.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT="$ROOT/infra/services/_user/rag-showcase"
ENV_FILE="$ROOT/infra/.env"

# 1. Compose overlay symlink (Atlas merges every services/_user/*/compose.yml).
mkdir -p "$SLOT"
ln -sf "../../../../compose/rag-overlay.yml" "$SLOT/compose.yml"
echo "Linked $SLOT/compose.yml -> compose/rag-overlay.yml"

# 2. Brand the vendored Atlas as rag-showcase. Atlas reads PROJECT_NAME and the
#    BRAND_* / BRAND_LOGO_FILE keys from infra/.env. Ensure .env exists first
#    (Atlas fills in generated secrets on first boot regardless), then set our
#    values idempotently. BRAND_LOGO_FILE is an absolute path derived from ROOT
#    so it works from any checkout location.
[ -f "$ENV_FILE" ] || cp "$ROOT/infra/.env.example" "$ENV_FILE"

set_env() {  # set_env KEY VALUE — replace the key (every occurrence) or append.
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
}

set_env PROJECT_NAME    "rag-showcase"
set_env BRAND_NAME      "RAG-SHOWCASE"
set_env BRAND_TAGLINE   "Six RAG approaches, side by side"
set_env BRAND_REPO_URL  "https://github.com/thekaveh/rag-showcase"
set_env BRAND_LOGO_FILE "$ROOT/brand/rag-showcase.logo"   # RAG-SHOWCASE block-art (ANSI-Shadow)
echo "Branded the Atlas stack as rag-showcase (PROJECT_NAME + BRAND_* + block-art logo)."
