from __future__ import annotations

import re
from pathlib import Path

import pytest
from PIL import Image

from scripts.docs.build_docs import render_mkdocs_yml, render_site, render_wiki
from scripts.docs.check_docs import check_local_links
from scripts.docs.links import is_forbidden
from scripts.docs.manifest import DOCS, first_h1, iter_pages, load_manifest


APPROACHES = [
    "vanilla-rag",
    "hybrid-rag",
    "contextual-rag",
    "graph-rag",
    "agentic-rag",
    "n8n-adaptive-rag",
    "lazy-graph-rag",
]


def test_manifest_h1s_match_numbered_titles() -> None:
    manifest = load_manifest()
    for page in iter_pages(manifest):
        assert first_h1((DOCS / page.source).read_text(encoding="utf-8")) == page.nav_label


def test_generated_surfaces_have_no_self_surface_links(tmp_path) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"
    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)
    for root, surface in [(site_dir, "site"), (wiki_dir, "wiki")]:
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
                assert not is_forbidden(match.group(1), surface), f"{path}: {match.group(1)}"


def test_generated_surfaces_publish_all_result_artifacts_and_have_valid_local_links(
    tmp_path,
) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"

    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)

    expected = {
        path.relative_to(DOCS / "results")
        for path in (DOCS / "results").rglob("*")
        if path.is_file() and path.suffix in {".json", ".jsonl"}
    }
    for root in (site_dir, wiki_dir):
        published = {
            path.relative_to(root / "results")
            for path in (root / "results").rglob("*")
            if path.is_file()
        }
        assert expected <= published
        check_local_links(root)


def test_generated_surfaces_publish_nested_approach_diagrams(tmp_path) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"

    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)

    for approach in APPROACHES:
        canonical = DOCS / "diagrams" / "approaches" / approach
        assert (canonical / "data-flow.html").is_file()
        assert (canonical / "data-flow.png").is_file()
        with Image.open(canonical / "data-flow.png") as rendered:
            assert rendered.size == (3600, 2000)

        site_target = site_dir / "assets" / "diagrams" / "approaches" / approach
        wiki_target = wiki_dir / "diagrams" / "approaches" / approach
        for target in (site_target, wiki_target):
            assert (target / "data-flow.html").is_file()
            assert (target / "data-flow.png").is_file()

    check_local_links(site_dir)
    check_local_links(wiki_dir)


def test_local_link_checker_rejects_missing_target(tmp_path) -> None:
    (tmp_path / "page.md").write_text(
        "[missing](results/evidence.jsonl)\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit, match="missing local link target"):
        check_local_links(tmp_path)


def test_generated_mkdocs_config_has_no_source_repo_links(tmp_path) -> None:
    manifest = load_manifest()
    target = tmp_path / "mkdocs.yml"
    render_mkdocs_yml(manifest, target)
    text = target.read_text(encoding="utf-8")
    assert "repo_url:" not in text
    assert "repo_name:" not in text
    assert "edit_uri:" not in text
    assert "docs_dir: generated/site" in text


def test_sortable_table_script_is_site_only_and_registered(tmp_path: Path) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"
    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)

    assert (site_dir / "javascripts" / "sortable-tables.js").is_file()
    assert not (wiki_dir / "javascripts" / "sortable-tables.js").exists()

    config = tmp_path / "mkdocs.yml"
    render_mkdocs_yml(manifest, config)
    assert "javascripts/sortable-tables.js" in config.read_text(encoding="utf-8")
