from __future__ import annotations

import pytest

from scripts.docs import check_docs


# check_manifest_h1/check_generated_content/check_readme are check_docs.py's own
# wrapper logic (build the failure message, call sys.exit) around already-tested
# primitives (first_h1, is_forbidden). Prior coverage only ever reimplemented
# their loop bodies inline (asserting the negative against real, compliant docs)
# rather than calling the functions themselves — so a regression in any of
# these functions' own `_fail()` conditions (an inverted comparison, a
# mis-anchored regex) would not be caught by `pytest tests/` at all, only by
# the separate `make docs-check` step, and only if that step happened to run
# against docs that currently violate the (possibly-broken) check.


class _FakePage:
    def __init__(self, source, nav_label):
        self.source = source
        self.nav_label = nav_label


def test_check_manifest_h1_passes_when_h1_matches(tmp_path, monkeypatch) -> None:
    (tmp_path / "page.md").write_text("# Correct Title\n\nbody\n", encoding="utf-8")
    monkeypatch.setattr(check_docs, "DOCS", tmp_path)
    monkeypatch.setattr(check_docs, "load_manifest", lambda: {})
    monkeypatch.setattr(
        check_docs, "iter_pages",
        lambda manifest: [_FakePage(tmp_path.__class__("page.md"), "Correct Title")],
    )

    check_docs.check_manifest_h1()  # must not raise


def test_check_manifest_h1_fails_when_h1_does_not_match_manifest(tmp_path, monkeypatch) -> None:
    (tmp_path / "page.md").write_text("# Wrong Title\n\nbody\n", encoding="utf-8")
    monkeypatch.setattr(check_docs, "DOCS", tmp_path)
    monkeypatch.setattr(check_docs, "load_manifest", lambda: {})
    monkeypatch.setattr(
        check_docs, "iter_pages",
        lambda manifest: [_FakePage(tmp_path.__class__("page.md"), "Correct Title")],
    )

    with pytest.raises(SystemExit, match="does not match manifest"):
        check_docs.check_manifest_h1()


def test_check_generated_content_passes_on_clean_surface(tmp_path, monkeypatch) -> None:
    site = tmp_path / "site"
    wiki = tmp_path / "wiki"
    site.mkdir()
    wiki.mkdir()
    (site / "page.md").write_text("# Title\n\nAll good, [a link](other.md).\n", encoding="utf-8")
    monkeypatch.setattr(check_docs, "SITE_SRC", site)
    monkeypatch.setattr(check_docs, "WIKI_SRC", wiki)

    check_docs.check_generated_content()  # must not raise


def test_check_generated_content_fails_on_leaked_placeholder_marker(tmp_path, monkeypatch) -> None:
    site = tmp_path / "site"
    wiki = tmp_path / "wiki"
    site.mkdir()
    wiki.mkdir()
    (site / "page.md").write_text("# Title\n\nTODO: finish this section.\n", encoding="utf-8")
    monkeypatch.setattr(check_docs, "SITE_SRC", site)
    monkeypatch.setattr(check_docs, "WIKI_SRC", wiki)

    with pytest.raises(SystemExit, match="placeholder marker leaked"):
        check_docs.check_generated_content()


def test_check_generated_content_fails_on_empty_fenced_block(tmp_path, monkeypatch) -> None:
    site = tmp_path / "site"
    wiki = tmp_path / "wiki"
    site.mkdir()
    wiki.mkdir()
    (site / "page.md").write_text("# Title\n\n```python\n```\n", encoding="utf-8")
    monkeypatch.setattr(check_docs, "SITE_SRC", site)
    monkeypatch.setattr(check_docs, "WIKI_SRC", wiki)

    with pytest.raises(SystemExit, match="empty fenced code block"):
        check_docs.check_generated_content()


def test_check_generated_content_fails_on_forbidden_cross_surface_link(tmp_path, monkeypatch) -> None:
    site = tmp_path / "site"
    wiki = tmp_path / "wiki"
    site.mkdir()
    wiki.mkdir()
    (site / "page.md").write_text(
        "# Title\n\nSee [the repo](https://github.com/thekaveh/rag-showcase).\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(check_docs, "SITE_SRC", site)
    monkeypatch.setattr(check_docs, "WIKI_SRC", wiki)

    with pytest.raises(SystemExit, match="forbidden cross-surface link"):
        check_docs.check_generated_content()


def test_check_readme_passes_when_publishing_mechanics_are_not_leaked(tmp_path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text(
        "# RAG Showcase\n\nA seven-approach RAG comparison.\n", encoding="utf-8",
    )
    monkeypatch.setattr(check_docs, "DOCS", tmp_path / "docs")

    check_docs.check_readme()  # must not raise


def test_check_readme_fails_when_it_mentions_mkdocs(tmp_path, monkeypatch) -> None:
    (tmp_path / "README.md").write_text(
        "# RAG Showcase\n\nBuilt with mkdocs.\n", encoding="utf-8",
    )
    monkeypatch.setattr(check_docs, "DOCS", tmp_path / "docs")

    with pytest.raises(SystemExit, match="leaks docs publishing mechanics"):
        check_docs.check_readme()
