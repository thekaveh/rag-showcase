#!/usr/bin/env python3
"""Export a bounded MITRE ATT&CK cyber-threat graph slice as markdown."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import httpx


ATTACK_URL = "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/enterprise-attack/enterprise-attack.json"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or "attack"


def _external_id(obj: dict) -> str:
    refs = obj.get("external_references") or []
    for ref in refs:
        if ref.get("external_id"):
            return ref["external_id"]
    return obj.get("id", "")


def _write_object(out: Path, idx: int, obj: dict, rels: list[dict]) -> None:
    name = obj.get("name") or obj.get("id")
    oid = obj.get("id")
    ext = _external_id(obj)
    outgoing = [r for r in rels if r.get("source_ref") == oid][:12]
    incoming = [r for r in rels if r.get("target_ref") == oid][:12]
    rel_lines = []
    for rel in outgoing:
        rel_lines.append(f"- {name} -> {rel.get('relationship_type')} -> {rel.get('target_ref')}")
    for rel in incoming:
        rel_lines.append(f"- {rel.get('source_ref')} -> {rel.get('relationship_type')} -> {name}")
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
    with httpx.Client(timeout=120.0) as client:
        resp = client.get(ATTACK_URL)
        resp.raise_for_status()
        objects = resp.json().get("objects", [])
    rels = [o for o in objects if o.get("type") == "relationship"]
    selected = [o for o in objects if o.get("type") in {
        "intrusion-set", "malware", "tool", "attack-pattern", "campaign", "course-of-action"
    }][:limit]
    for idx, obj in enumerate(selected, start=1):
        _write_object(output, idx, obj, rels)
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
