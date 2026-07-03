from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APPROACHES = [
    "vanilla-rag",
    "hybrid-rag",
    "contextual-rag",
    "graph-rag",
    "agentic-rag",
    "n8n-adaptive-rag",
]


def test_approach_internals_doc_covers_every_approach_and_tuning_surface() -> None:
    doc = (ROOT / "docs" / "approaches.md").read_text(encoding="utf-8")

    for approach in APPROACHES:
        assert f"`{approach}`" in doc

    assert "Hybrid retrieval" in doc
    assert "Graph RAG" in doc
    assert "hybrid-rag` is not a graph-RAG approach" in doc

    for knob in [
        "RETRIEVE_K",
        "TOP_N",
        "alpha",
        "LIGHTRAG_QUERY_TOP_K",
        "LIGHTRAG_QUERY_CHUNK_TOP_K",
        "LIGHTRAG_QUERY_MAX_TOTAL_TOKENS",
        "MAX_STEPS",
        "N8N_ADAPTIVE_WEBHOOK_URL",
    ]:
        assert knob in doc


def test_main_docs_link_to_approach_internals() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    comparison = (ROOT / "docs" / "comparison.md").read_text(encoding="utf-8")

    assert "docs/approaches.md" in readme
    assert "approaches.md" in architecture
    assert "approaches.md" in comparison


def test_flavor_tuning_doc_is_linked_and_covers_invocation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    doc = (ROOT / "docs" / "approach-flavor-tuning.md").read_text(encoding="utf-8")

    assert "docs/approach-flavor-tuning.md" in readme
    assert "OpenWebUI" in doc
    assert "graph-rag-wide" in doc
    assert "MATRIX_FLAVORS" in doc
    assert "compare/flavors.yaml" in doc
