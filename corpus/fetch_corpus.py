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
        print(f"⚠ MultiHop-RAG fetch skipped ({e}). Keyword docs only — "
              f"add your own .md files to {RAW} for a richer demo.")


if __name__ == "__main__":
    main()
