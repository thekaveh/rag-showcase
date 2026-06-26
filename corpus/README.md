# Corpus

`python corpus/fetch_corpus.py` populates `corpus/raw/` with a MultiHop-RAG
subset (multi-hop + thematic news) plus the hand-picked keyword docs in
`keyword_docs/`. `raw/` is gitignored; the script is the source of truth.
Requires `pip install datasets` for the MultiHop-RAG slice.
