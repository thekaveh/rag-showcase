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

    for base in sorted(BASE_APPROACHES):
        _CACHE[base] = _default(base)

    path = _path()
    if not path.is_file():
        return _CACHE

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
        if base not in BASE_APPROACHES:
            raise KeyError(f"flavor {alias!r} uses unknown base approach {base!r}")
        params = row.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"flavor {alias!r} params must be an object")
        _CACHE[alias] = FlavorProfile(
            alias=alias,
            base=base,
            label=str(row.get("label") or alias),
            description=str(row.get("description") or ""),
            requires_reingest=bool(row.get("requires_reingest", False)),
            params=dict(params),
        )
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
