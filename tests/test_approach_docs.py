from __future__ import annotations

from pathlib import Path

import yaml


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


def test_every_approach_section_embeds_its_data_flow_diagram() -> None:
    doc = (ROOT / "docs" / "approaches.md").read_text(encoding="utf-8")

    for approach in APPROACHES:
        base = f"diagrams/approaches/{approach}/data-flow"
        assert f"![{approach} service and data flow]({base}.png)" in doc
        assert f"[Open the full-resolution interactive diagram]({base}.html)" in doc


def test_approach_diagram_labels_match_implementation_contracts() -> None:
    required_labels = {
        "contextual-rag": ["Weaviate · RagBase", "Showcase post-step", "RagContextual"],
        "graph-rag": ["Graph/vector lookup", "query profile selects optional TEI"],
        "agentic-rag": ["vector_top_k", "graph_mode", "MAX_STEPS=4"],
        "n8n-adaptive-rag": ["simple | complex", "vanilla-rag", "agentic-rag"],
        "lazy-graph-rag": ["NO LIGHTRAG", "NO NEO4J", "Graph cache volume"],
    }

    for approach, labels in required_labels.items():
        path = ROOT / "docs" / "diagrams" / "approaches" / approach / "data-flow.html"
        html = path.read_text(encoding="utf-8")
        for label in labels:
            assert label in html


def test_main_docs_link_to_approach_internals() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    architecture = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")
    comparison = (ROOT / "docs" / "comparison.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    manifest = yaml.safe_load((ROOT / "docs" / "manifest.yaml").read_text(encoding="utf-8"))
    manifest_sources = {
        page["source"]
        for section in manifest["sections"]
        for page in section["pages"]
    }

    assert "docs/approaches.md" in readme
    assert "approaches.md" in architecture
    assert "approaches.md" in comparison
    assert "docs/evaluation-methodology.md" in readme
    assert "evaluation-methodology.md" in comparison
    assert "backend_plugins/rag/plugin.yml" in readme
    assert "evaluation-results.md" in manifest_sources
    assert "[Full sortable leaderboards](evaluation-results.md)" in index
    assert "docs/evaluation-results.md" in readme
    assert "[complete leaderboards](evaluation-results.md)" in comparison


def test_comparison_defers_aggregate_metrics_to_canonical_leaderboards() -> None:
    comparison = (ROOT / "docs" / "comparison.md").read_text(encoding="utf-8")

    assert "evaluation-results.md" in comparison
    for aggregate_literal in [
        "4.17",
        "4.31",
        "3.17",
        "12.61",
        "12.47",
        "21.20",
        "4.58",
        "4.19",
        "3.67",
    ]:
        assert aggregate_literal not in comparison, (
            "comparison interpretation must defer aggregate result metrics to "
            "the canonical evaluation-results.md leaderboards"
        )


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
        "2026-07-17",
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
