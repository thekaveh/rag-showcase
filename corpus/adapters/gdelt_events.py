#!/usr/bin/env python3
"""Export a bounded GDELT article/event slice as markdown dossiers."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import httpx


API = "https://api.gdeltproject.org/api/v2/doc/doc"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:72] or "event"


def _write_article(out: Path, idx: int, article: dict, query: str) -> None:
    title = article.get("title") or article.get("url") or f"GDELT article {idx}"
    url = article.get("url") or ""
    domain = article.get("domain") or ""
    date = article.get("seendate") or ""
    source_country = article.get("sourcecountry") or ""
    language = article.get("language") or ""
    text = (
        f"# {title}\n\n"
        f"Source: {url}\n\n"
        f"Dataset query: {query}\n"
        f"Seen date: {date}\n"
        f"Domain: {domain}\n"
        f"Source country: {source_country}\n"
        f"Language: {language}\n\n"
        "Summary:\n"
        f"{article.get('socialimage') or article.get('url') or 'GDELT article record'}\n\n"
        "Relations:\n"
        f"- {title} -> source_domain -> {domain}\n"
        f"- {title} -> seen_on -> {date}\n"
        f"- {title} -> source_country -> {source_country}\n"
        f"- {title} -> matched_query -> {query}\n"
    )
    (out / f"{idx:03d}-{_slug(title)}.md").write_text(text, encoding="utf-8")


def export(query: str, start: str, end: str, output: Path, limit: int) -> int:
    output.mkdir(parents=True, exist_ok=True)
    params = {
        "query": query,
        "mode": "artlist",
        "format": "json",
        "maxrecords": min(limit, 250),
        "startdatetime": start,
        "enddatetime": end,
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.get(API, params=params)
        resp.raise_for_status()
        articles = resp.json().get("articles", [])[:limit]
    for idx, article in enumerate(articles, start=1):
        _write_article(output, idx, article, query)
    return len(articles)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--start", required=True, help="YYYYMMDDHHMMSS")
    parser.add_argument("--end", required=True, help="YYYYMMDDHHMMSS")
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export(args.query, args.start, args.end, args.output, args.limit)
    print(f"wrote {count} GDELT docs to {args.output}")


if __name__ == "__main__":
    main()
