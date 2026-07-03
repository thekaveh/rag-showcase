#!/usr/bin/env python3
"""Export a bounded MITRE ATT&CK cyber-threat graph slice as markdown."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import httpx


ATTACK_URL = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"
TYPE_ORDER = [
    "intrusion-set",
    "campaign",
    "malware",
    "tool",
    "attack-pattern",
    "course-of-action",
]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or "attack"


def _external_id(obj: dict) -> str:
    refs = obj.get("external_references") or []
    for ref in refs:
        if ref.get("external_id"):
            return ref["external_id"]
    return obj.get("id", "")


def _display(obj_id: str, objects_by_id: dict[str, dict]) -> str:
    obj = objects_by_id.get(obj_id) or {}
    name = obj.get("name")
    ext = _external_id(obj) if obj else ""
    if name and ext:
        return f"{name} ({ext})"
    return name or obj_id


def _write_object(
    out: Path,
    idx: int,
    obj: dict,
    rels: list[dict],
    objects_by_id: dict[str, dict],
) -> None:
    name = obj.get("name") or obj.get("id")
    oid = obj.get("id")
    ext = _external_id(obj)
    outgoing = [r for r in rels if r.get("source_ref") == oid][:12]
    incoming = [r for r in rels if r.get("target_ref") == oid][:12]
    rel_lines = []
    for rel in outgoing:
        rel_lines.append(
            f"- {name} -> {rel.get('relationship_type')} -> "
            f"{_display(str(rel.get('target_ref') or ''), objects_by_id)}"
        )
    for rel in incoming:
        rel_lines.append(
            f"- {_display(str(rel.get('source_ref') or ''), objects_by_id)} -> "
            f"{rel.get('relationship_type')} -> {name}"
        )
    if not rel_lines:
        rel_lines.append(f"- {name} -> appears_in -> MITRE ATT&CK Enterprise")

    text = (
        f"# {name}\n\n"
        f"Source: MITRE ATT&CK Enterprise STIX bundle\n\n"
        f"Object type: {obj.get('type')}\n"
        f"ATT&CK ID: {ext}\n"
        f"STIX ID: {oid}\n\n"
        f"Description:\n{obj.get('description') or '(no description)'}\n\n"
        "Relations:\n" + "\n".join(rel_lines) + "\n"
    )
    (out / f"{idx:03d}-{_slug(ext or name)}.md").write_text(text, encoding="utf-8")


def export(output: Path, limit: int) -> int:
    output.mkdir(parents=True, exist_ok=True)
    for stale in output.glob("*.md"):
        stale.unlink()
    with httpx.Client(timeout=120.0) as client:
        resp = client.get(ATTACK_URL)
        resp.raise_for_status()
        objects = resp.json().get("objects", [])
    rels = [o for o in objects if o.get("type") == "relationship"]
    objects_by_id = {o.get("id"): o for o in objects if o.get("id")}
    candidates = [o for o in objects if o.get("type") in set(TYPE_ORDER)]
    related_ids = {
        ref
        for rel in rels
        for ref in (rel.get("source_ref"), rel.get("target_ref"))
        if ref
    }
    related = sorted(
        (o for o in candidates if o.get("id") in related_ids),
        key=lambda o: (_external_id(o), o.get("name", "")),
    )
    selected: list[dict] = []
    per_type = max(1, limit // len(TYPE_ORDER))
    for obj_type in TYPE_ORDER:
        selected.extend([o for o in related if o.get("type") == obj_type][:per_type])
    if len(selected) < limit:
        selected_ids = {o.get("id") for o in selected}
        selected.extend([o for o in related if o.get("id") not in selected_ids][:limit - len(selected)])
    selected = selected[:limit]
    for idx, obj in enumerate(selected, start=1):
        _write_object(output, idx, obj, rels, objects_by_id)
    return len(selected)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export(args.output, args.limit)
    print(f"wrote {count} ATT&CK docs to {args.output}")


if __name__ == "__main__":
    main()
