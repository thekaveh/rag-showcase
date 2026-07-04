"""Named RAG approach flavors.

A flavor is a reproducible alias for a base approach plus parameter overrides.
Canonical approach names always resolve to a default empty profile, so adding
flavors never changes the six stable endpoints.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


BASE_APPROACHES = {
    "vanilla-rag",
    "hybrid-rag",
    "contextual-rag",
    "graph-rag",
    "agentic-rag",
    "n8n-adaptive-rag",
}


@dataclass(frozen=True)
class FlavorProfile:
    alias: str
    base: str
    label: str = "Default"
    description: str = ""
    requires_reingest: bool = False
    params: dict[str, Any] = field(default_factory=dict)


_CACHE: dict[str, FlavorProfile] = {}

# Params the handlers coerce with int()/float() per request. Validate the types at
# load time so a typo'd value (e.g. retrieve_k: "4o") fails fast and consistently
# instead of turning into an unexplained per-request 500 hours after the edit.
_NUMERIC_PARAMS: dict[str, type] = {
    "k": int, "retrieve_k": int, "top_n": int, "alpha": float, "max_steps": int,
    "vector_top_k": int, "top_k": int, "chunk_top_k": int, "max_total_tokens": int,
}
# Bool params get the same load-time strictness: a quoted "false" is truthy, so a
# hand-edited rerank: "false" would silently INVERT the intent per request.
_BOOL_PARAMS = {"rerank", "enable_rerank"}


def _path() -> Path:
    return Path(os.getenv("RAG_FLAVORS_FILE", "/app/plugins/rag/flavors.yaml"))


def _profile_copy(profile: FlavorProfile) -> FlavorProfile:
    return FlavorProfile(
        alias=profile.alias,
        base=profile.base,
        label=profile.label,
        description=profile.description,
        requires_reingest=profile.requires_reingest,
        params=dict(profile.params),
    )


def _default(alias: str) -> FlavorProfile:
    return FlavorProfile(alias=alias, base=alias)


def _load() -> dict[str, FlavorProfile]:
    if _CACHE:
        return _CACHE

    # Build the full table in a local dict and publish it to the module cache only
    # after the whole file validates. A malformed flavors.yaml then raises on EVERY
    # call (consistently) instead of poisoning _CACHE with a partial table that the
    # `if _CACHE` short-circuit above would silently return on later calls — dropping
    # every flavor defined after the bad row. Mirrors config._load's atomic .update().
    table: dict[str, FlavorProfile] = {
        base: _default(base) for base in sorted(BASE_APPROACHES)
    }

    path = _path()
    if path.is_file():
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        rows = data.get("flavors") or []
        if not isinstance(rows, list):
            raise ValueError(f"{path} must contain a list under 'flavors'")

        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"{path} contains a non-object flavor entry")
            alias = str(row.get("alias") or "").strip()
            base = str(row.get("base") or "").strip()
            if not alias:
                raise ValueError(f"{path} contains a flavor without alias")
            if alias in BASE_APPROACHES:
                # Enforce the module contract stated above: the canonical six always
                # resolve to their default profile. A row shadowing a base name would
                # silently change what the stable endpoints mean (and a cross-base
                # shadow would 500 that canonical endpoint outright).
                raise ValueError(f"flavor alias {alias!r} shadows a canonical base approach")
            if alias in table:
                raise ValueError(f"duplicate flavor alias {alias!r}")
            if base not in BASE_APPROACHES:
                raise KeyError(f"flavor {alias!r} uses unknown base approach {base!r}")
            params = row.get("params") or {}
            if not isinstance(params, dict):
                raise ValueError(f"flavor {alias!r} params must be an object")
            params = dict(params)
            for key, cast in _NUMERIC_PARAMS.items():
                if key not in params:
                    continue
                try:
                    params[key] = cast(params[key])
                except (TypeError, ValueError) as e:
                    raise ValueError(
                        f"flavor {alias!r} param {key!r} must be "
                        f"{cast.__name__}-compatible, got {params[key]!r}") from e
                # Range-check too: an out-of-range alpha or a zero/negative limit
                # passes the type gate but fails per-request downstream — the exact
                # deferred-500 class this load-time guard exists to prevent.
                if key == "alpha":
                    if not 0.0 <= params[key] <= 1.0:
                        raise ValueError(
                            f"flavor {alias!r} param 'alpha' must be within [0, 1], "
                            f"got {params[key]!r}")
                elif params[key] < 1:
                    raise ValueError(
                        f"flavor {alias!r} param {key!r} must be >= 1, "
                        f"got {params[key]!r}")
            for key in _BOOL_PARAMS:
                if key in params and not isinstance(params[key], bool):
                    raise ValueError(
                        f"flavor {alias!r} param {key!r} must be true/false, "
                        f"got {params[key]!r}")
            table[alias] = FlavorProfile(
                alias=alias,
                base=base,
                label=str(row.get("label") or alias),
                description=str(row.get("description") or ""),
                requires_reingest=bool(row.get("requires_reingest", False)),
                params=params,
            )

    _CACHE.update(table)
    return _CACHE


def get(alias_or_base: str) -> FlavorProfile:
    if alias_or_base.startswith("openai/"):
        alias_or_base = alias_or_base.split("/", 1)[1]
    profiles = _load()
    if alias_or_base not in profiles:
        raise KeyError(f"unknown RAG flavor or approach {alias_or_base!r}")
    return _profile_copy(profiles[alias_or_base])


def get_for_base(alias_or_base: str, base: str) -> FlavorProfile:
    profile = get(alias_or_base)
    if profile.base != base:
        raise KeyError(
            f"RAG flavor {alias_or_base!r} uses base {profile.base!r}, not {base!r}"
        )
    return profile


def aliases_for_base(base: str) -> list[str]:
    if base not in BASE_APPROACHES:
        raise KeyError(f"unknown base approach {base!r}")
    profiles = _load()
    return [p.alias for p in profiles.values() if p.base == base]
