from __future__ import annotations

import re
from pathlib import Path

import pytest

import shutil

from scripts.docs import render_diagrams
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


def test_home_is_explicitly_unnumbered_without_weakening_content_page_numbers() -> None:
    pages = iter_pages(load_manifest())
    home = next(page for page in pages if page.source.as_posix() == "index.md")
    content = next(page for page in pages if page.source.as_posix() == "guide/overview.md")

    assert home.display_number is False
    assert home.nav_label == "RAG Showcase"
    assert content.display_number is True
    assert content.nav_label == "2.1 Overview"


def test_first_h1_skips_hash_lines_inside_code_fences() -> None:
    # No committed doc page happens to have a "# " line inside a code fence
    # before its real title, so the in_fence tracking guard was previously
    # unverified — a fenced example command/comment starting with "# " must
    # not be mistaken for the page's H1.
    text = "```\n# not a title\n```\n\n# Real Title\n\nbody\n"
    assert first_h1(text) == "Real Title"


def test_first_h1_returns_none_when_absent() -> None:
    assert first_h1("no heading here, just prose\n") is None


def test_first_h1_accepts_centered_html_heading() -> None:
    assert first_h1('<h1 align="center">RAG Showcase</h1>\n') == "RAG Showcase"


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


def test_generated_wiki_uses_native_gollum_markdown(tmp_path) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    wiki_dir = tmp_path / "wiki"
    render_wiki(manifest, pages, wiki_dir)

    home = (wiki_dir / "Home.md").read_text(encoding="utf-8")
    assert not home.startswith("---\n")
    assert 'class="hero-tagline"' not in home
    assert 'class="grid cards"' not in home
    assert " markdown>" not in home
    assert "{ .md-button" not in home

    for path in wiki_dir.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
            target = match.group(1).split("#", 1)[0]
            if "://" not in target:
                assert not target.endswith(".md"), f"{path}: raw wiki page link {target}"


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
    # Pillow is only a transitive dependency of the `docs` group (via cairosvg);
    # a plain `uv sync` (no --group docs) — what `make test`/README's documented
    # `uv run pytest` command actually run — never installs it, so this import
    # must be deferred and skippable rather than a module-level `from PIL import
    # Image`, which would fail collection for the whole file on a fresh clone.
    Image = pytest.importorskip("PIL.Image")
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


def test_generated_surfaces_publish_landscape_comparison_overview(tmp_path) -> None:
    Image = pytest.importorskip("PIL.Image")
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"

    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)

    master = DOCS / "diagrams" / "rag-showcase-comparison-overview.html"
    canonical_png = DOCS / "diagrams" / "img" / "rag-showcase-comparison-overview.png"
    assert master.is_file()
    assert canonical_png.is_file()
    with Image.open(canonical_png) as rendered:
        width, height = rendered.size
        assert width >= 2400
        assert width > height

    site_svg = site_dir / "assets" / "img" / "rag-showcase-comparison-overview.svg"
    assert site_svg.is_file()
    assert 'xmlns="http://www.w3.org/2000/svg"' in site_svg.read_text(
        encoding="utf-8"
    )
    assert (
        site_dir / "assets" / "img" / "rag-showcase-comparison-overview.png"
    ).is_file()
    assert (wiki_dir / "img" / "rag-showcase-comparison-overview.png").is_file()


def test_generated_surfaces_publish_the_brand_banner(tmp_path) -> None:
    Image = pytest.importorskip("PIL.Image")
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"

    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)

    canonical = DOCS / "brand" / "rag-showcase-banner.png"
    with Image.open(canonical) as rendered:
        width, height = rendered.size
        assert width >= 3600
        assert width == height * 3

    assert (site_dir / "assets" / "brand" / canonical.name).is_file()
    assert (wiki_dir / "img" / canonical.name).is_file()
    assert "assets/brand/rag-showcase-banner.png" in (
        site_dir / "index.md"
    ).read_text(encoding="utf-8")
    assert "img/rag-showcase-banner.png" in (wiki_dir / "Home.md").read_text(
        encoding="utf-8"
    )


def test_brand_banner_master_labels_every_retrieval_lane() -> None:
    html = (DOCS / "brand" / "rag-showcase-banner.html").read_text(
        encoding="utf-8"
    )

    assert '<h1 class="banner__title">RAG SHOWCASE</h1>' in html
    aliases = [
        "vanilla-rag",
        "hybrid-rag",
        "contextual-rag",
        "graph-rag",
        "agentic-rag",
        "n8n-adaptive-rag",
        "lazy-graph-rag",
    ]
    positions = [html.index(f">{alias}</span>") for alias in aliases]

    assert positions == sorted(positions)
    assert html.count('class="lane-label ') == 7
    assert "font-size: 56px" in html
    assert "font-size: 21px" in html


def test_render_all_regenerates_a_missing_nested_approach_png(tmp_path, monkeypatch) -> None:
    # render_all()'s cairosvg fallback used to only ever glob html_dir's own
    # top-level *.html, so the seven nested diagrams/approaches/<name>/
    # data-flow.html files were silently skipped: a missing nested PNG (e.g.
    # after an SVG edit without the manual headless-Chrome re-render in
    # docs/architecture.md §6) would never be regenerated by `make docs-build`.
    # Work on a temp copy of docs/diagrams so this doesn't touch the real
    # committed PNGs, and delete one nested PNG to force the fallback path.
    # Stub svg_to_png rather than requiring a real cairosvg/libcairo install
    # (the `docs` dependency group only guarantees the Python package, and
    # its `surface` submodule dlopen's the native libcairo at import time) —
    # this test is about render_all()'s file-discovery and placement, not
    # about cairosvg's actual rendering.
    written: list[Path] = []

    def _fake_svg_to_png(svg_path: Path, png_path: Path) -> None:
        # png_path is the unique temp path _render_fallback_png renders into
        # (then atomically publishes to the real target via os.replace), not
        # the final target itself — assert against target_png's own content
        # below, not against this callback's argument.
        written.append(png_path)
        png_path.parent.mkdir(parents=True, exist_ok=True)
        png_path.write_bytes(b"fake-png")

    monkeypatch.setattr(render_diagrams, "svg_to_png", _fake_svg_to_png)

    tmp_docs = tmp_path / "docs"
    shutil.copytree(DOCS / "diagrams", tmp_docs / "diagrams")
    other_approach, target_approach = "vanilla-rag", "hybrid-rag"
    other_png = tmp_docs / "diagrams" / "approaches" / other_approach / "data-flow.png"
    target_png = tmp_docs / "diagrams" / "approaches" / target_approach / "data-flow.png"
    other_bytes_before = other_png.read_bytes()
    target_png.unlink()

    monkeypatch.setattr(render_diagrams, "DOCS", tmp_docs)
    render_diagrams.render_all()

    assert len(written) == 1, "missing nested-approach PNG was never regenerated"
    # svg_to_png must render into a temp path distinct from the final target
    # and then get atomically published via os.replace — not write straight
    # into the shared final path, which two concurrent local `build()`
    # invocations could otherwise interleave/truncate.
    assert written[0] != target_png, (
        "svg_to_png wrote directly to the shared final path instead of a "
        "temp path meant to be published atomically")
    assert target_png.is_file()
    assert target_png.read_bytes() == b"fake-png"
    # The atomic-publish temp file must not survive the call.
    leftover = list(target_png.parent.glob(".tmp-*"))
    assert leftover == [], f"temp PNG not cleaned up: {leftover}"
    # The untouched sibling approach must survive byte-for-byte: the fallback
    # must only fill in what's missing, never overwrite an existing PNG.
    assert other_png.read_bytes() == other_bytes_before


def test_local_link_checker_rejects_missing_target(tmp_path) -> None:
    (tmp_path / "page.md").write_text(
        "[missing](results/evidence.jsonl)\n", encoding="utf-8"
    )

    with pytest.raises(SystemExit, match="missing local link target"):
        check_local_links(tmp_path)


def test_generated_site_rewrites_interactive_diagram_iframe_src(tmp_path) -> None:
    # The interactive diagrams embed their HTML via <iframe src="...">. That src is
    # an HTML attribute (not a markdown link), so the link rewriter skips it; the
    # transform must rewrite it separately to the assets/ path on the site or the
    # inline iframe 404s (only the "Open full size" fallback would work).
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    render_site(manifest, pages, site_dir)

    for page in ("diagrams/architecture.md", "diagrams/approach-flows.md"):
        text = (site_dir / page).read_text(encoding="utf-8")
        match = re.search(r'<iframe[^>]*\bsrc="([^"]+)"', text)
        assert match, f"{page}: no iframe found"
        src = match.group(1)
        assert src.startswith("../assets/diagrams/"), f"{page}: iframe src not rewritten: {src}"
        # the referenced HTML asset is actually published beside the page
        assert (site_dir / page).parent.joinpath(src).is_file(), f"{page}: iframe target missing: {src}"


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

    leaderboard = next(page for page in pages if page.source.as_posix() == "evaluation-results.md")
    for path in (site_dir / leaderboard.source, wiki_dir / leaderboard.wiki_name):
        text = path.read_text(encoding="utf-8")
        assert '<table class="results-table" id="base-overall">' in text
        assert '<table class="results-table" id="flavor-overall">' in text

    config = tmp_path / "mkdocs.yml"
    render_mkdocs_yml(manifest, config)
    assert "javascripts/sortable-tables.js" in config.read_text(encoding="utf-8")


def test_sortable_table_css_does_not_overlay_horizontally_scrolled_headers() -> None:
    css = (DOCS / "stylesheets" / "extra.css").read_text(encoding="utf-8")

    assert ".results-table th:first-child" not in css


def test_docs_workflow_runs_leaderboard_python_and_browser_contract_tests() -> None:
    workflow = (DOCS.parent / ".github" / "workflows" / "docs.yml").read_text(
        encoding="utf-8"
    )
    makefile = (DOCS.parent / "Makefile").read_text(encoding="utf-8")

    # CI runs these through `make test`/`make lint`/`make sortable-tables-test`
    # (single source of truth shared with local dev, per README §8) rather than
    # duplicating the raw commands — assert both that CI invokes the targets and
    # that the targets still run the real commands, so a Makefile edit can't
    # silently drop coverage.
    assert "run: make test" in workflow
    assert "run: make lint" in workflow
    assert "run: make sortable-tables-test" in workflow
    assert "uv run pytest tests backend_plugins/rag/tests -q" in makefile
    assert "uv run ruff check ." in makefile
    assert "node --test tests/docs/test_sortable_tables.cjs" in makefile


def test_docs_workflow_validates_all_changes_and_requires_wiki_credentials() -> None:
    workflow = (DOCS.parent / ".github" / "workflows" / "docs.yml").read_text(
        encoding="utf-8"
    )

    assert "    paths:" not in workflow
    assert "Require wiki deploy key" in workflow
    assert "WIKI_DEPLOY_KEY is required" in workflow
    assert "Skip wiki publish" not in workflow
    assert "if: env.WIKI_DEPLOY_KEY != ''" not in workflow
