"""Build the showcase contextual index from Atlas-ingested plain chunks."""
from __future__ import annotations

import argparse
import asyncio
from collections import defaultdict
from pathlib import Path

from rag.common import litellm, vectors
from rag.common.contextual import contextualize


def _document_text(
    corpus_root: Path,
    source: str,
    chunks: list[vectors.IngestedChunk],
) -> str:
    path = (corpus_root / source).resolve()
    root = corpus_root.resolve()
    if root == path or root in path.parents:
        if path.suffix.lower() in {".txt", ".md"}:
            try:
                return path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    return "\n\n".join(chunk.text for chunk in chunks)


async def run(
    *,
    corpus_root: str = "/app/corpus",
    base_collection: str = vectors.BASE_COLLECTION,
    contextual_collection: str = vectors.CONTEXTUAL_COLLECTION,
) -> dict[str, str | int]:
    chunks = await asyncio.to_thread(vectors.read_ingested_chunks, base_collection)
    if not chunks:
        raise RuntimeError(
            f"no Atlas-ingested chunks found in {base_collection!r}; "
            "refusing to rebuild the contextual collection empty"
        )

    grouped: dict[str, list[vectors.IngestedChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.source].append(chunk)

    rows: list[dict] = []
    root = Path(corpus_root)
    for source in sorted(grouped):
        source_chunks = sorted(grouped[source], key=lambda chunk: chunk.index)
        document = _document_text(root, source, source_chunks)
        for chunk in source_chunks:
            blurb = await contextualize(document, chunk.text)
            rows.append({"title": source, "text": f"{blurb}\n\n{chunk.text}"})

    embeddings = await litellm.embed([row["text"] for row in rows])
    if len(embeddings) != len(rows):
        raise RuntimeError(
            f"contextual embedding count mismatch: {len(embeddings)} vectors "
            f"for {len(rows)} Atlas chunks"
        )
    indexed = [{**row, "vector": vector} for row, vector in zip(rows, embeddings)]

    await asyncio.to_thread(vectors.delete_collection, contextual_collection)
    await asyncio.to_thread(vectors.ensure_collection, contextual_collection)
    count = await asyncio.to_thread(vectors.add_chunks, contextual_collection, indexed)
    return {
        "base_collection": base_collection,
        "source_chunks": len(chunks),
        "contextual_collection": contextual_collection,
        "contextual_chunks": count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", default="/app/corpus")
    parser.add_argument("--base-collection", default=vectors.BASE_COLLECTION)
    parser.add_argument("--contextual-collection", default=vectors.CONTEXTUAL_COLLECTION)
    args = parser.parse_args()
    print(
        asyncio.run(
            run(
                corpus_root=args.corpus_root,
                base_collection=args.base_collection,
                contextual_collection=args.contextual_collection,
            )
        )
    )


if __name__ == "__main__":
    main()
