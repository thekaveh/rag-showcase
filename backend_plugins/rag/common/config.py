"""Role→model resolution and shared env accessors."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

_log = logging.getLogger("uvicorn.error")

_CACHE: dict[str, str] = {}
# A missing/empty roles file yields an empty _CACHE, which is falsy — so gating
# the cache on `_CACHE` truthiness would treat that as a miss and re-stat +
# re-warn on every role lookup (2+ per request). Cache the *loaded* state itself
# so the negative result is remembered and the warning fires exactly once.
_LOADED = False


def _load() -> dict[str, str]:
    global _LOADED
    if _LOADED:
        return _CACHE
    path = Path(os.environ.get("RAG_ROLES_FILE", "/app/plugins/rag/roles.yaml"))
    if not path.is_file():
        # A missing roles file (broken mount, typo'd RAG_ROLES_FILE) previously
        # loaded {} silently and every request 500'd on the first role lookup with
        # nothing in the logs to say why.
        _log.warning("roles file %s not found; every role lookup will fail", path)
        data = {}
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data and not isinstance(data, dict):
        # Same operator-error class as flavors._load's ValueError style.
        raise ValueError(f"{path} must contain a mapping of role -> model")
    _CACHE.update({str(k): str(v) for k, v in (data or {}).items()})
    _LOADED = True
    return _CACHE


def role(name: str) -> str:
    """Return the LiteLLM model configured for ``name``; KeyError if unset."""
    table = _load()
    if name not in table:
        raise KeyError(f"role '{name}' not defined in roles.yaml")
    return table[name]


def litellm_base() -> str:
    return os.environ.get("LITELLM_BASE_URL", "http://litellm:4000").rstrip("/")


def litellm_key() -> str:
    return os.environ.get("LITELLM_API_KEY", "")
