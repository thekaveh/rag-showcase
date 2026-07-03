#!/usr/bin/env python3
"""Export a bounded OpenAlex works slice as relation-heavy markdown dossiers."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import httpx


API = "https://api.openalex.org/works"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or "work"


def _abstract(index: dict | None) -> str:
    if not index:
        return ""
    words: list[tuple[int, str]] = []
    for word, positions in index.items():
        for pos in positions:
            words.append((int(pos), word))
    return " ".join(word for _, word in sorted(words))


def _write_work(out: Path, idx: int, work: dict) -> None:
    title = work.get("title") or work.get("display_name") or work.get("id") or "Untitled work"
    authors = [a.get("author", {}).get("display_name") for a in work.get("authorships", [])]
    authors = [a for a in authors if a]
    concepts = [c.get("display_name") for c in work.get("concepts", [])[:8] if c.get("display_name")]
    institutions = []
    for authorship in work.get("authorships", []):
        for inst in authorship.get("institutions", []):
            if inst.get("display_name"):
                institutions.append(inst["display_name"])
    abstract = _abstract(work.get("abstract_inverted_index"))
    refs = work.get("referenced_works", [])[:8]
    source = ((work.get("primary_location") or {}).get("source") or {}).get("display_name") or "unknown venue"
    url = work.get("doi") or work.get("id") or ""

    rels = [
        f"- {title} -> published_in -> {source}",
        *[f"- {title} -> authored_by -> {a}" for a in authors[:8]],
        *[f"- {title} -> affiliated_with -> {i}" for i in sorted(set(institutions))[:8]],
        *[f"- {title} -> has_concept -> {c}" for c in concepts],
        *[f"- {title} -> cites -> {r}" for r in refs],
    ]
    text = (
        f"# {title}\n\n"
        f"Source: {url}\n\n"
        f"Venue: {source}\n"
        f"Authors: {', '.join(authors[:12]) or 'unknown'}\n"
        f"Concepts: {', '.join(concepts) or 'unknown'}\n\n"
        f"Abstract:\n{abstract or '(no abstract in OpenAlex record)'}\n\n"
        "Relations:\n" + "\n".join(rels) + "\n"
    )
    (out / f"{idx:03d}-{_slug(title)}.md").write_text(text, encoding="utf-8")


def export(search: str, output: Path, limit: int) -> int:
    output.mkdir(parents=True, exist_ok=True)
    # Idempotent re-export: drop prior-run docs so a shrinking slice can't leave
    # stale higher-index files behind for ingest to pick up (mirrors cyber_threat_intel).
    for stale in output.glob("*.md"):
        stale.unlink()
    params = {"search": search, "per-page": min(limit, 200), "sort": "cited_by_count:desc"}
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(API, params=params)
        resp.raise_for_status()
        works = resp.json().get("results", [])[:limit]
    for idx, work in enumerate(works, start=1):
        _write_work(output, idx, work)
    return len(works)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", required=True)
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export(args.search, args.output, args.limit)
    print(f"wrote {count} OpenAlex docs to {args.output}")


if __name__ == "__main__":
    main()
