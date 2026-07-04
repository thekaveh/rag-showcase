"""Assemble the curated corpus: a small MultiHop-RAG subset + keyword docs.

MultiHop-RAG (Tang & Yang, 2024) is distributed on Hugging Face under
`yixuantt/MultiHopRAG`. We take a small slice of its corpus for fast indexing.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

RAW = Path(__file__).parent / "raw"
KEYWORD = Path(__file__).parent / "keyword_docs"
MAX_DOCS = 40


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    # Idempotent re-assembly: drop prior-run docs so a smaller MAX_DOCS or a
    # changed MultiHop-RAG slice can't leave stale higher-index files behind for
    # ingest's **/*.md glob to pick up (mirrors the corpus/adapters/* exporters).
    for stale in RAW.glob("*.md"):
        stale.unlink()
    # Keyword docs (always included)
    for p in KEYWORD.glob("*.md"):
        shutil.copy(p, RAW / p.name)
    # MultiHop-RAG corpus slice
    try:
        from datasets import load_dataset
        ds = load_dataset("yixuantt/MultiHopRAG", "corpus", split="train")
        for i, row in enumerate(ds):
            if i >= MAX_DOCS:
                break
            title = (row.get("title") or f"doc-{i}").replace("/", "-")[:80]
            body = row.get("body") or row.get("text") or json.dumps(row)
            (RAW / f"{i:03d}-{title}.md").write_text(f"# {title}\n\n{body}", encoding="utf-8")
        print(f"Wrote {min(MAX_DOCS, len(ds))} MultiHop-RAG docs + keyword docs to {RAW}")
    except Exception as e:  # offline / dataset unavailable
        print(f"⚠ MultiHop-RAG fetch skipped ({e}). Keyword docs only — add "
              f"durable .md files under {KEYWORD} for a richer demo ({RAW} is "
              f"purged and rebuilt on every run).")


if __name__ == "__main__":
    import argparse

    # Zero-option parser: makes --help safe (it used to purge and rebuild corpus/raw)
    # and rejects stray arguments.
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    ).parse_args()
    main()
