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

set_env_default() {  # set_env_default KEY VALUE — set only when absent or empty.
  local key="$1" val="$2" current=""
  current="$(grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
  if [ -z "$current" ]; then
    set_env "$key" "$val"
  fi
}

append_csv_env() {  # append_csv_env KEY VALUE — idempotently append a CSV item.
  local key="$1" val="$2" current=""
  current="$(grep -E "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2- || true)"
  if [ -z "$current" ]; then
    set_env "$key" "$val"
    return
  fi
  case ",$current," in
    *,"$val",*) ;;
    *) set_env "$key" "${current},${val}" ;;
  esac
}

set_env PROJECT_NAME    "rag-showcase"
set_env BRAND_NAME      "RAG-SHOWCASE"
set_env BRAND_TAGLINE   "Six RAG approaches, side by side"
set_env BRAND_REPO_URL  "https://github.com/thekaveh/rag-showcase"
set_env BRAND_LOGO_FILE "$ROOT/brand/rag-showcase.logo"   # RAG-SHOWCASE block-art (ANSI-Shadow)

# Configure Atlas through its public LightRAG inputs. These defaults are
# intentionally written only when the user has not already chosen values in
# infra/.env; Atlas then renders them into LightRAG's native runtime env.
LIGHTRAG_ROLE_MODEL_DEFAULT="${RAG_SHOWCASE_LIGHTRAG_ROLE_MODEL:-mistral-small3.2:24b}"
set_env_default LIGHTRAG_EMBEDDING_MODEL "nomic-embed-text"
set_env_default LIGHTRAG_EXTRACT_LLM_MODEL "$LIGHTRAG_ROLE_MODEL_DEFAULT"
set_env_default LIGHTRAG_KEYWORD_LLM_MODEL "$LIGHTRAG_ROLE_MODEL_DEFAULT"
set_env_default LIGHTRAG_QUERY_LLM_MODEL "$LIGHTRAG_ROLE_MODEL_DEFAULT"
set_env_default LIGHTRAG_EXTRACT_MAX_ASYNC_LLM "1"
set_env_default LIGHTRAG_EXTRACT_LLM_TIMEOUT "900"
append_csv_env OLLAMA_CUSTOM_MODELS "$LIGHTRAG_ROLE_MODEL_DEFAULT"

echo "Branded the Atlas stack as rag-showcase (PROJECT_NAME + BRAND_* + block-art logo)."
