from __future__ import annotations

from pathlib import Path

from scripts.docs.opener import (
    CANONICAL_BADGES,
    CANONICAL_POWERED_BY,
    CANONICAL_SUMMARY,
    CANONICAL_TAGLINE,
    check_canonical_openers,
    marked_block,
)


ROOT = Path(__file__).resolve().parents[2]


def test_canonical_openers_match_every_full_shared_block() -> None:
    check_canonical_openers(ROOT)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    expected = {
        "tagline": CANONICAL_TAGLINE,
        "summary": CANONICAL_SUMMARY,
        "badges": CANONICAL_BADGES,
        "powered-by": CANONICAL_POWERED_BY,
    }
    for name, value in expected.items():
        assert marked_block(readme, name) == value
        assert marked_block(index, name) == value


def test_executive_summary_is_concise_grounded_and_evidence_aware() -> None:
    words = CANONICAL_SUMMARY.split()
    assert 100 <= len(words) <= 150
    assert "response envelope with available evidence and metrics" in CANONICAL_SUMMARY
    assert "uniform retrieved-context" not in CANONICAL_SUMMARY
    assert "controlled comparison" in CANONICAL_SUMMARY
    assert "Open WebUI" in CANONICAL_SUMMARY


def test_openers_embed_the_shared_poster_and_complete_stack_line() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert (
        "![RAG Showcase comparison flow]"
        "(docs/diagrams/img/rag-showcase-poster.png)" in readme
    )
    assert (
        "![RAG Showcase comparison flow]"
        "(diagrams/img/rag-showcase-poster.png)" in index
    )
    for technology in [
        "Atlas",
        "Open WebUI",
        "LiteLLM",
        "Weaviate",
        "LightRAG",
        "Neo4j",
        "Supabase/Postgres",
        "Chonkie",
        "TEI",
        "n8n",
        "Ollama-compatible providers",
        "Ragas",
        "blinded judge panel",
    ]:
        assert technology in CANONICAL_POWERED_BY


def test_opener_results_links_target_canonical_sections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert (
        "docs/dataset-complexity-report.md#5-base-family-per-query-winners"
        in readme
    )
    assert "[Measured Results](evaluation-results.md){ .md-button }" in index
