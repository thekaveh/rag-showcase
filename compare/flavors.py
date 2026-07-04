"""Flavor manifest helpers for comparison runs."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "compare" / "flavors.yaml"
BASE_APPROACHES = [
    "vanilla-rag",
    "hybrid-rag",
    "contextual-rag",
    "graph-rag",
    "agentic-rag",
    "n8n-adaptive-rag",
]


@dataclass(frozen=True)
class FlavorProfile:
    alias: str
    base: str
    flavor: str = "default"
    label: str = "Default"
    description: str = ""
    requires_reingest: bool = False
    params: dict[str, Any] = field(default_factory=dict)


def _default(alias: str) -> FlavorProfile:
    return FlavorProfile(alias=alias, base=alias)


def load_flavors(manifest: Path = DEFAULT_MANIFEST) -> dict[str, FlavorProfile]:
    profiles = {base: _default(base) for base in BASE_APPROACHES}
    if not manifest.is_file():
        return profiles

    data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
    rows = data.get("flavors") or []
    if not isinstance(rows, list):
        raise ValueError(f"{manifest} must contain a list under 'flavors'")

    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{manifest} contains a non-object flavor entry")
        alias = str(row.get("alias") or "").strip()
        base = str(row.get("base") or "").strip()
        if not alias:
            raise ValueError(f"{manifest} contains a flavor without alias")
        if alias in BASE_APPROACHES:
            # The canonical six always resolve to their default profile; a manifest
            # row shadowing a base name would silently change what "default" means.
            raise ValueError(f"flavor alias {alias!r} shadows a canonical base approach")
        if alias in profiles:
            raise ValueError(f"duplicate flavor alias {alias!r}")
        if base not in BASE_APPROACHES:
            raise KeyError(f"flavor {alias!r} uses unknown base approach {base!r}")
        params = row.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError(f"flavor {alias!r} params must be an object")
        profiles[alias] = FlavorProfile(
            alias=alias,
            base=base,
            # removeprefix, not replace: replace() would rewrite the substring
            # anywhere in the alias and mislabel odd prefixes.
            flavor=str(row.get("flavor") or alias.removeprefix(f"{base}-") or "default"),
            label=str(row.get("label") or alias),
            description=str(row.get("description") or ""),
            requires_reingest=bool(row.get("requires_reingest", False)),
            params=dict(params),
        )
    return profiles


def profile_for_model(model: str, manifest: Path = DEFAULT_MANIFEST) -> FlavorProfile:
    profiles = load_flavors(manifest)
    if model not in profiles:
        raise KeyError(f"unknown RAG approach/flavor {model!r}")
    return profiles[model]


def expand_selection(selection: list[str], manifest: Path = DEFAULT_MANIFEST) -> list[FlavorProfile]:
    profiles = load_flavors(manifest)
    out: list[FlavorProfile] = []
    seen: set[str] = set()
    for item in selection:
        if item == "default":
            candidates = [profiles[base] for base in BASE_APPROACHES]
        elif item in BASE_APPROACHES:
            candidates = [p for p in profiles.values() if p.base == item]
        else:
            candidates = [profile_for_model(item, manifest)]
        for profile in candidates:
            if profile.alias not in seen:
                out.append(profile)
                seen.add(profile.alias)
    return out
