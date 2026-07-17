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
    "lazy-graph-rag",
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
    assert "docs/evaluation-methodology.md" in readme
    assert "evaluation-methodology.md" in comparison
    assert "backend_plugins/rag/plugin.yml" in readme


def test_flavor_tuning_doc_is_linked_and_covers_invocation() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    doc = (ROOT / "docs" / "approach-flavor-tuning.md").read_text(encoding="utf-8")

    assert "docs/approach-flavor-tuning.md" in readme
    assert "Open WebUI" in doc
    assert "graph-rag-wide" in doc
    assert "MATRIX_FLAVORS" in doc
    assert "compare/flavors.yaml" in doc


def test_experimental_lazy_graph_design_is_linked_and_measured() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    approaches = (ROOT / "docs" / "approaches.md").read_text(encoding="utf-8")
    design = (ROOT / "docs" / "lazy-graph-rag.md").read_text(encoding="utf-8")

    assert "docs/lazy-graph-rag.md" in readme
    assert "`lazy-graph-rag`" in approaches
    for phrase in [
        "Experimental",
        "LLM-free",
        "relevance_budget",
        "seed_k",
        "max_context_chunks",
        "content fingerprint",
        "2026-07-13",
        "cyber_threat_intel",
    ]:
        assert phrase in design


def test_evaluation_methodology_documents_models_judges_and_ladder() -> None:
    doc = (ROOT / "docs" / "evaluation-methodology.md").read_text(encoding="utf-8")

    for phrase in [
        "Model Roles",
        "Approach Processes",
        "Dataset-Ladder Procedure",
        "Judgment Panel",
        "qwen3.6:latest",
        "gemma4:31b",
        "mistral-small3.2:24b",
        "nomic-embed-text",
        "baseline_curated",
        "graph_native",
        "cyber_threat_intel",
    ]:
        assert phrase in doc
