from __future__ import annotations

from pathlib import Path

from scripts.docs import opener
from scripts.docs.opener import (
    CANONICAL_BADGES,
    CANONICAL_SUPPORT,
    CANONICAL_SUMMARY,
    CANONICAL_TAGLINE,
    CANONICAL_TECH_BADGES,
    CANONICAL_TITLE,
    check_canonical_openers,
    marked_block,
)


ROOT = Path(__file__).resolve().parents[2]


def test_openers_use_the_shared_brand_first_visual_hierarchy() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    title = '<h1 align="center">RAG Showcase</h1>'
    for text, banner in [
        (readme, "docs/brand/rag-showcase-banner.png"),
        (index, "brand/rag-showcase-banner.png"),
    ]:
        assert banner in text
        assert title in text
        assert text.index(banner) < text.index(title)
        assert '<p align="center">' in text
        assert "Quick Start" in text
        assert "Measured Results" in text
        assert "Architecture" in text


def test_technology_showcase_is_grouped_logo_bearing_shields() -> None:
    assert hasattr(opener, "CANONICAL_SUPPORT")
    assert hasattr(opener, "CANONICAL_TECH_BADGES")
    tech_badges = getattr(opener, "CANONICAL_TECH_BADGES", "")

    assert tech_badges.count("<p align=\"center\">") == 3
    assert tech_badges.count("<img ") >= 13
    assert tech_badges.count("logo=") >= 7
    for technology in [
        "Atlas",
        "Open WebUI",
        "LiteLLM",
        "FastAPI",
        "Weaviate",
        "LightRAG",
        "Neo4j",
        "Supabase",
        "Chonkie",
        "TEI",
        "n8n",
        "Ollama",
        "Ragas",
    ]:
        assert technology.replace(" ", "%20") in tech_badges or technology in tech_badges


def test_readme_latest_results_callout_stays_compact() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    start = readme.index("<!-- opener:results -->")
    end = readme.index("<!-- /opener:results -->")
    callout = readme[start:end]

    assert len(callout.splitlines()) <= 8
    assert "380/380" in callout
    assert "docs/evaluation-results.md" in callout


def test_canonical_openers_match_every_full_shared_block() -> None:
    check_canonical_openers(ROOT)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    expected = {
        "title": CANONICAL_TITLE,
        "tagline": CANONICAL_TAGLINE,
        "support": CANONICAL_SUPPORT,
        "summary": CANONICAL_SUMMARY,
        "badges": CANONICAL_BADGES,
        "tech-badges": CANONICAL_TECH_BADGES,
    }
    for name, value in expected.items():
        expected_value = " ".join(value.split())
        assert marked_block(readme, name) == expected_value
        assert marked_block(index, name) == expected_value


def test_executive_summary_is_concise_grounded_and_evidence_aware() -> None:
    words = CANONICAL_SUMMARY.split()
    assert 100 <= len(words) <= 150
    assert "response envelope with available evidence and metrics" in CANONICAL_SUMMARY
    assert "uniform retrieved-context" not in CANONICAL_SUMMARY
    assert "controlled comparison" in CANONICAL_SUMMARY
    assert "Open WebUI" in CANONICAL_SUMMARY


def test_openers_embed_the_shared_banner_and_complete_stack_shields() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert (
        "![Seven retrieval paths converging on one measured comparison]"
        "(docs/brand/rag-showcase-banner.png)" in readme
    )
    assert (
        "![Seven retrieval paths converging on one measured comparison]"
        "(brand/rag-showcase-banner.png)" in index
    )
    for technology in [
        "Atlas",
        "Open WebUI",
        "LiteLLM",
        "Weaviate",
        "LightRAG",
        "Neo4j",
        "Supabase",
        "Chonkie",
        "TEI",
        "n8n",
        "Ollama",
        "Ragas",
    ]:
        assert technology in CANONICAL_TECH_BADGES


def test_opener_results_links_target_canonical_sections() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    index = (ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert 'href="docs/evaluation-results.md"' in readme
    assert 'href="evaluation-results.md"' in index
