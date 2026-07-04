"""Role→model resolution and shared env accessors."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import yaml

_log = logging.getLogger("uvicorn.error")

_CACHE: dict[str, str] = {}


def _load() -> dict[str, str]:
    if _CACHE:
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
    return _CACHE


def role(name: str) -> str:
    """Return the LiteLLM model configured for ``name``; KeyError if unset."""
    table = _load()
    if name not in table:
        raise KeyError(f"role '{name}' not defined in roles.yaml")
    return table[name]


_MODELS_CACHE: dict[str, dict] = {}


def _load_models() -> dict[str, dict]:
    if _MODELS_CACHE:
        return _MODELS_CACHE
    path = Path(os.environ.get("RAG_MODELS_FILE", "/app/plugins/rag/models.yaml"))
    if not path.is_file():
        _log.warning("models file %s not found; no per-model params will apply", path)
        data = {}
    else:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data and not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping of model -> params")
    for k, v in (data or {}).items():
        if v is not None and not isinstance(v, dict):
            raise ValueError(f"{path}: params for model {k!r} must be a mapping")
    _MODELS_CACHE.update({str(k): dict(v or {}) for k, v in (data or {}).items()})
    return _MODELS_CACHE


def model_params(model: str) -> dict:
    """Per-model request properties (e.g. {'think': False}) declared in models.yaml,
    merged into chat requests for that LiteLLM model. Scoped by model name: a model
    not listed returns {} — so flipping a role to an unlisted (e.g. cloud) model
    sends nothing extra."""
    return dict(_load_models().get(model, {}))


def litellm_base() -> str:
    return os.environ.get("LITELLM_BASE_URL", "http://litellm:4000").rstrip("/")


def litellm_key() -> str:
    return os.environ.get("LITELLM_API_KEY", "")
