# Corpus

## 1. Contents

`corpus/` provides the curated showcase corpus: a MultiHop-RAG subset (multi-hop
+ thematic news) plus the hand-picked keyword docs in `keyword_docs/` (rare
identifiers like `WIDGET-ERR-7741` that exercise the exact-keyword contrast). The
populated `corpus/raw/` directory is gitignored; `fetch_corpus.py` is the source
of truth.

## 2. Setup

```bash
python corpus/fetch_corpus.py
```

This copies the keyword docs into `corpus/raw/` and appends a MultiHop-RAG slice.
The MultiHop-RAG slice needs the optional `datasets` dependency:

```bash
uv sync --group corpus    # or: pip install datasets
```

If `datasets` is unavailable, the script degrades gracefully to keyword-docs only.
