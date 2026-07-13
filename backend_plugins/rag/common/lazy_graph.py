"""Deterministic, LLM-free concept graph used by experimental lazy-graph-rag."""
from __future__ import annotations

import hashlib
import heapq
import json
import os
import re
import time
import uuid
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Any

from .vectors import Hit

INDEX_VERSION = 1
_TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9_.-]{2,}\b")
_PHRASE = re.compile(
    r"\b[A-Z][A-Za-z0-9_.-]{2,}(?:\s+[A-Z][A-Za-z0-9_.-]{2,}){1,3}\b"
)
_STOP = {
    "about", "after", "also", "among", "and", "are", "because", "been", "before",
    "being", "between", "both", "but", "can", "could", "does", "each", "for",
    "from", "had", "has", "have", "into", "its", "may", "more", "most", "not",
    "over", "such", "than", "that", "the", "their", "then", "there", "these",
    "they", "this", "through", "under", "using", "was", "were", "what", "when",
    "where", "which", "while", "who", "will", "with", "would", "your",
}


def _normal(value: str) -> str:
    return " ".join(value.lower().split())


def extract_concepts(text: str, *, max_concepts: int = 24) -> list[str]:
    """Extract stable concepts without model calls or heavyweight NLP packages."""
    positions: dict[str, int] = {}
    counts: Counter[str] = Counter()
    for match in _PHRASE.finditer(text):
        concept = _normal(match.group(0))
        positions.setdefault(concept, match.start())
        counts[concept] += 2
    for match in _TOKEN.finditer(text):
        concept = _normal(match.group(0)).strip(".-_")
        if concept in _STOP or len(concept) < 3:
            continue
        positions.setdefault(concept, match.start())
        counts[concept] += 1
    ordered = sorted(counts, key=lambda item: (-counts[item], positions[item], item))
    return ordered[:max(1, max_concepts)]


def chunk_id(hit: Hit) -> str:
    digest = hashlib.sha256()
    digest.update(hit.title.encode("utf-8"))
    digest.update(b"\0")
    digest.update(hit.text.encode("utf-8"))
    return digest.hexdigest()[:24]


def corpus_fingerprint(chunks: list[Hit], *, max_concepts_per_chunk: int = 24) -> str:
    digest = hashlib.sha256(
        f"lazy-graph-index:{INDEX_VERSION}:concepts={max_concepts_per_chunk}\n".encode()
    )
    for hit in sorted(chunks, key=lambda item: (item.title, item.text)):
        digest.update(hit.title.encode("utf-8"))
        digest.update(b"\0")
        digest.update(hit.text.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()


@dataclass(frozen=True)
class GraphChunk:
    id: str
    title: str
    text: str
    concepts: tuple[str, ...]


@dataclass(frozen=True)
class GraphIndex:
    fingerprint: str
    chunks: dict[str, GraphChunk]
    concept_chunks: dict[str, tuple[str, ...]]
    edges: dict[str, dict[str, int]]

    @property
    def edge_count(self) -> int:
        return sum(len(neighbors) for neighbors in self.edges.values()) // 2

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": INDEX_VERSION,
            "fingerprint": self.fingerprint,
            "chunks": {
                key: {
                    "id": chunk.id,
                    "title": chunk.title,
                    "text": chunk.text,
                    "concepts": list(chunk.concepts),
                }
                for key, chunk in sorted(self.chunks.items())
            },
            "concept_chunks": {
                key: list(value) for key, value in sorted(self.concept_chunks.items())
            },
            "edges": {
                key: dict(sorted(value.items())) for key, value in sorted(self.edges.items())
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GraphIndex":
        if data.get("version") != INDEX_VERSION:
            raise ValueError("unsupported lazy graph index version")
        chunks = {
            key: GraphChunk(
                id=str(row["id"]),
                title=str(row["title"]),
                text=str(row["text"]),
                concepts=tuple(str(item) for item in row["concepts"]),
            )
            for key, row in dict(data["chunks"]).items()
        }
        return cls(
            fingerprint=str(data["fingerprint"]),
            chunks=chunks,
            concept_chunks={
                key: tuple(str(item) for item in value)
                for key, value in dict(data["concept_chunks"]).items()
            },
            edges={
                key: {neighbor: int(weight) for neighbor, weight in value.items()}
                for key, value in dict(data["edges"]).items()
            },
        )


@dataclass(frozen=True)
class BuildStats:
    cache_hit: bool
    index_seconds: float
    chunk_count: int
    concept_count: int
    edge_count: int


@dataclass(frozen=True)
class RetrievalResult:
    hits: list[Hit]
    relevance_tests: int
    visited_concepts: tuple[str, ...]


def build_index(chunks: list[Hit], *, max_concepts_per_chunk: int = 24) -> GraphIndex:
    graph_chunks: dict[str, GraphChunk] = {}
    concept_chunks: dict[str, set[str]] = {}
    edges: dict[str, Counter[str]] = {}
    for hit in sorted(chunks, key=lambda item: (item.title, item.text)):
        identifier = chunk_id(hit)
        concepts = tuple(extract_concepts(
            f"{hit.title}. {hit.text}", max_concepts=max_concepts_per_chunk
        ))
        graph_chunks[identifier] = GraphChunk(identifier, hit.title, hit.text, concepts)
        for concept in concepts:
            concept_chunks.setdefault(concept, set()).add(identifier)
            edges.setdefault(concept, Counter())
        for left, right in combinations(sorted(set(concepts)), 2):
            edges[left][right] += 1
            edges[right][left] += 1
    return GraphIndex(
        fingerprint=corpus_fingerprint(
            chunks, max_concepts_per_chunk=max_concepts_per_chunk
        ),
        chunks=graph_chunks,
        concept_chunks={key: tuple(sorted(value)) for key, value in concept_chunks.items()},
        edges={key: dict(value) for key, value in edges.items()},
    )


def _stats(index: GraphIndex, *, cache_hit: bool, started: float) -> BuildStats:
    return BuildStats(
        cache_hit=cache_hit,
        index_seconds=time.monotonic() - started,
        chunk_count=len(index.chunks),
        concept_count=len(index.concept_chunks),
        edge_count=index.edge_count,
    )


def load_or_build(
    chunks: list[Hit], *, cache_dir: str | Path, namespace: str,
    max_concepts_per_chunk: int = 24,
) -> tuple[GraphIndex, BuildStats]:
    """Load a matching index or atomically replace it when corpus content changes."""
    started = time.monotonic()
    directory = Path(cache_dir)
    directory.mkdir(parents=True, exist_ok=True)
    safe_namespace = re.sub(r"[^A-Za-z0-9_.-]+", "-", namespace).strip(".-") or "default"
    path = directory / f"{safe_namespace}.json"
    fingerprint = corpus_fingerprint(
        chunks, max_concepts_per_chunk=max_concepts_per_chunk
    )
    if path.is_file():
        try:
            cached = GraphIndex.from_dict(json.loads(path.read_text(encoding="utf-8")))
            if cached.fingerprint == fingerprint:
                return cached, _stats(cached, cache_hit=True, started=started)
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            pass

    index = build_index(chunks, max_concepts_per_chunk=max_concepts_per_chunk)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(
        json.dumps(index.to_dict(), sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    temporary.replace(path)
    return index, _stats(index, cache_hit=False, started=started)


def retrieve(
    index: GraphIndex,
    question: str,
    *,
    seed_hits: list[Hit],
    relevance_budget: int,
    max_context_chunks: int,
) -> RetrievalResult:
    """Expand query/seed concepts under a hard budget and rank linked chunks."""
    chunk_scores: Counter[str] = Counter()
    queue: list[tuple[float, str]] = []
    best_queued: dict[str, float] = {}

    def enqueue(concept: str, score: float) -> None:
        if concept not in index.concept_chunks or score <= best_queued.get(concept, 0.0):
            return
        best_queued[concept] = score
        heapq.heappush(queue, (-score, concept))

    for concept in extract_concepts(question, max_concepts=16):
        enqueue(concept, 4.0)
    for rank, hit in enumerate(seed_hits):
        identifier = chunk_id(hit)
        seed_score = 3.0 / (rank + 1)
        if identifier in index.chunks:
            chunk_scores[identifier] += seed_score
            for concept in index.chunks[identifier].concepts:
                enqueue(concept, seed_score)

    visited: list[str] = []
    while queue and len(visited) < max(1, relevance_budget):
        negative_score, concept = heapq.heappop(queue)
        if concept in visited:
            continue
        score = -negative_score
        visited.append(concept)
        for identifier in index.concept_chunks.get(concept, ()):
            chunk_scores[identifier] += score
        neighbors = index.edges.get(concept, {})
        max_weight = max(neighbors.values(), default=1)
        ordered_neighbors = sorted(neighbors.items(), key=lambda item: (-item[1], item[0]))
        for neighbor, weight in ordered_neighbors[:16]:
            enqueue(neighbor, score * 0.5 * (weight / max_weight))

    if chunk_scores:
        ranked_ids = sorted(
            chunk_scores,
            key=lambda identifier: (
                -chunk_scores[identifier],
                index.chunks[identifier].title,
                identifier,
            ),
        )[:max(1, max_context_chunks)]
        hits = [
            Hit(
                index.chunks[identifier].title,
                index.chunks[identifier].text,
                float(chunk_scores[identifier]),
            )
            for identifier in ranked_ids
        ]
    else:
        hits = seed_hits[:max(1, max_context_chunks)]
    return RetrievalResult(hits, len(visited), tuple(visited))
