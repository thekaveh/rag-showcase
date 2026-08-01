from __future__ import annotations

from pathlib import Path


CANONICAL_TAGLINE = (
    "Seven RAG approaches compared side by side through one Atlas stack and one "
    "reproducible evaluation harness."
)

CANONICAL_SUMMARY = (
    "RAG Showcase serves seven retrieval strategies as OpenAI-compatible model aliases "
    "in Open WebUI, so one prompt can fan out across vanilla, hybrid, contextual, "
    "LightRAG graph, agentic, n8n-adaptive, and experimental lazy-graph retrieval. "
    "Atlas supplies the shared gateway, model routing, ingestion, stores, workflow "
    "services, and health lifecycle; this repository contributes the approach plugin, "
    "corpus ladder, tuning flavors, and evaluation harness. The differentiator is "
    "controlled comparison rather than a collection of disconnected demos: approaches "
    "consume the same dataset profile and embedding model, return one response envelope "
    "with available evidence and metrics, and are scored from persisted artifacts by "
    "Ragas and a blinded judge panel. The default stack can run locally, while provider "
    "and model choices remain configurable through Atlas."
)

CANONICAL_BADGES = (
    "![Docs and tests](https://img.shields.io/github/actions/workflow/status/thekaveh/"
    "rag-showcase/docs.yml?branch=develop&label=docs%20%26%20tests) "
    "![Atlas consumer contract](https://img.shields.io/github/actions/workflow/status/"
    "thekaveh/rag-showcase/atlas-contract.yml?branch=develop&label=Atlas%20contract) "
    "![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-2563eb.svg)"
)

CANONICAL_POWERED_BY = (
    "**Powered by:** Platform and UX: Atlas · Open WebUI · LiteLLM | Retrieval and "
    "storage: Weaviate · LightRAG · Neo4j · Supabase/Postgres | Processing and "
    "workflow: Chonkie · TEI · n8n | Models and evaluation: Ollama-compatible "
    "providers · Ragas · blinded judge panel"
)

_EXPECTED = {
    "tagline": CANONICAL_TAGLINE,
    "summary": CANONICAL_SUMMARY,
    "badges": CANONICAL_BADGES,
    "powered-by": CANONICAL_POWERED_BY,
}


class OpenerError(ValueError):
    pass


def _normalize(value: str) -> str:
    return " ".join(value.split())


def marked_block(text: str, name: str) -> str:
    start = f"<!-- opener:{name} -->"
    end = f"<!-- /opener:{name} -->"
    if text.count(start) != 1 or text.count(end) != 1:
        raise OpenerError(f"opener block {name!r} must have exactly one marker pair")
    before, remainder = text.split(start, 1)
    value, after = remainder.split(end, 1)
    if end in before or start in after:
        raise OpenerError(f"opener block {name!r} markers are malformed")
    return _normalize(value)


def check_canonical_openers(root: Path) -> None:
    surfaces = {
        "README.md": root / "README.md",
        "docs/index.md": root / "docs" / "index.md",
    }
    for label, path in surfaces.items():
        text = path.read_text(encoding="utf-8")
        for name, expected in _EXPECTED.items():
            actual = marked_block(text, name)
            if actual != expected:
                raise OpenerError(
                    f"{label}: opener block {name!r} differs from the canonical string"
                )

    summary_words = len(CANONICAL_SUMMARY.split())
    if not 100 <= summary_words <= 150:
        raise OpenerError(
            f"canonical executive summary has {summary_words} words; expected 100-150"
        )

    required_posters = {
        "README.md": "(docs/diagrams/img/rag-showcase-poster.png)",
        "docs/index.md": "(diagrams/img/rag-showcase-poster.png)",
    }
    for label, target in required_posters.items():
        text = surfaces[label].read_text(encoding="utf-8")
        if f"![RAG Showcase comparison flow]{target}" not in text:
            raise OpenerError(f"{label}: shared opener poster is missing")
