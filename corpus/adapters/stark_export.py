#!/usr/bin/env python3
"""Export a bounded STaRK SKB slice as markdown dossiers.

This adapter requires the optional `stark-qa` package. It keeps the generated
output intentionally small because LightRAG extraction is the expensive part of
the comparison.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or "item"


def _node_text(node: Any) -> str:
    if isinstance(node, dict):
        parts = []
        for key in ("title", "name", "description", "abstract", "text"):
            if node.get(key):
                parts.append(f"{key}: {node[key]}")
        return "\n".join(parts) or json.dumps(node, ensure_ascii=False)[:2000]
    return str(node)


def _write_doc(out: Path, idx: int, dataset: str, node_id: Any, node: Any) -> None:
    title = f"{dataset}:{node_id}"
    body = _node_text(node)
    text = (
        f"# {title}\n\n"
        f"Source: STaRK {dataset} semi-structured knowledge base.\n\n"
        f"Dataset: {dataset}\n"
        f"Node ID: {node_id}\n\n"
        f"Description:\n{body}\n\n"
        "Relations:\n"
        "- exported_node -> belongs_to_dataset -> STaRK\n"
        f"- {title} -> appears_in -> STaRK-{dataset}\n"
    )
    (out / f"{idx:03d}-{_slug(title)}.md").write_text(text, encoding="utf-8")


def export(dataset: str, output: Path, limit: int) -> int:
    try:
        from stark_qa import load_skb  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "stark-qa is not installed. Install with: python3 -m pip install stark-qa"
        ) from exc

    skb = load_skb(dataset, download_processed=True, root=None)
    output.mkdir(parents=True, exist_ok=True)
    # Idempotent re-export: drop prior-run docs so a shrinking slice can't leave
    # stale higher-index files behind for ingest to pick up (mirrors cyber_threat_intel).
    for stale in output.glob("*.md"):
        stale.unlink()

    node_ids = list(getattr(skb, "node_info", {}).keys())[:limit]
    if not node_ids and hasattr(skb, "candidate_ids"):
        node_ids = list(skb.candidate_ids)[:limit]

    for idx, node_id in enumerate(node_ids, start=1):
        node = getattr(skb, "node_info", {}).get(node_id, node_id)
        _write_doc(output, idx, dataset, node_id, node)
    return len(node_ids)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=["prime", "mag", "amazon"], required=True)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    count = export(args.dataset, args.output, args.limit)
    print(f"wrote {count} STaRK {args.dataset} docs to {args.output}")


if __name__ == "__main__":
    sys.exit(main())
