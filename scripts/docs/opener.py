from __future__ import annotations

from pathlib import Path


CANONICAL_TITLE = '<h1 align="center">RAG Showcase</h1>'

CANONICAL_TAGLINE = (
    '<p align="center"><strong>Seven RAG approaches. One shared stack. '
    "Measured side by side.</strong></p>"
)

CANONICAL_SUPPORT = (
    '<p align="center">Compare vector, hybrid, contextual, graph, agentic, adaptive, '
    "and lazy-graph retrieval through one reproducible Atlas evaluation harness.</p>"
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

CANONICAL_BADGES = """<p align="center">
  <img alt="Docs and tests" src="https://img.shields.io/github/actions/workflow/status/thekaveh/rag-showcase/docs.yml?branch=main&amp;label=docs%20%26%20tests">
  <img alt="Atlas consumer contract" src="https://img.shields.io/github/actions/workflow/status/thekaveh/rag-showcase/atlas-contract.yml?branch=main&amp;label=Atlas%20contract">
  <img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-2563eb.svg">
</p>"""

CANONICAL_TECH_BADGES = """<p align="center">
  <img alt="Atlas" src="https://img.shields.io/badge/Atlas-platform-0891b2">
  <img alt="Open WebUI" src="https://img.shields.io/badge/Open%20WebUI-chat-111827?logo=openwebui&amp;logoColor=white">
  <img alt="LiteLLM" src="https://img.shields.io/badge/LiteLLM-gateway-0f766e?logo=litellm&amp;logoColor=white">
  <img alt="FastAPI" src="https://img.shields.io/badge/FastAPI-plugin%20API-009688?logo=fastapi&amp;logoColor=white">
</p>
<p align="center">
  <img alt="Weaviate" src="https://img.shields.io/badge/Weaviate-vector%20store-00b3b3?logo=weaviate&amp;logoColor=white">
  <img alt="LightRAG" src="https://img.shields.io/badge/LightRAG-knowledge%20graph-7c3aed">
  <img alt="Neo4j" src="https://img.shields.io/badge/Neo4j-graph%20store-4581c3?logo=neo4j&amp;logoColor=white">
  <img alt="Supabase and PostgreSQL" src="https://img.shields.io/badge/Supabase%20%2F%20Postgres-state-3ecf8e?logo=supabase&amp;logoColor=white">
</p>
<p align="center">
  <img alt="Chonkie" src="https://img.shields.io/badge/Chonkie-chunking-f59e0b">
  <img alt="TEI" src="https://img.shields.io/badge/TEI-reranking-f97316">
  <img alt="n8n" src="https://img.shields.io/badge/n8n-workflows-ea4b71?logo=n8n&amp;logoColor=white">
  <img alt="Ollama" src="https://img.shields.io/badge/Ollama-local%20models-111827?logo=ollama&amp;logoColor=white">
  <img alt="Ragas" src="https://img.shields.io/badge/Ragas-evaluation-2563eb">
</p>"""

_EXPECTED = {
    "title": CANONICAL_TITLE,
    "tagline": CANONICAL_TAGLINE,
    "support": CANONICAL_SUPPORT,
    "summary": CANONICAL_SUMMARY,
    "badges": CANONICAL_BADGES,
    "tech-badges": CANONICAL_TECH_BADGES,
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
            if actual != _normalize(expected):
                raise OpenerError(
                    f"{label}: opener block {name!r} differs from the canonical string"
                )

    summary_words = len(CANONICAL_SUMMARY.split())
    if not 100 <= summary_words <= 150:
        raise OpenerError(
            f"canonical executive summary has {summary_words} words; expected 100-150"
        )

    required_banners = {
        "README.md": "(docs/brand/rag-showcase-banner.png)",
        "docs/index.md": "(brand/rag-showcase-banner.png)",
    }
    for label, target in required_banners.items():
        text = surfaces[label].read_text(encoding="utf-8")
        if f"![Seven retrieval paths converging on one measured comparison]{target}" not in text:
            raise OpenerError(f"{label}: shared brand banner is missing")
