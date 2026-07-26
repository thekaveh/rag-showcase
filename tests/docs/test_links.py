from __future__ import annotations

import pytest

from scripts.docs.links import is_forbidden, strip_forbidden_links


# is_forbidden is the whole reason this module exists — it decides which links
# get stripped from generated site/wiki docs. The only prior coverage
# (test_three_surface_docs.py's is_forbidden assertion) only ever exercises
# the negative case against real generated docs, none of which happen to trip
# any of the four forbidding branches — every `return True` was unverified.
@pytest.mark.parametrize("target, surface", [
    ("https://github.com/thekaveh/rag-showcase/blob/main/README.md", "site"),
    ("https://github.com/thekaveh/rag-showcase", "wiki"),
    ("https://thekaveh.github.io/rag-showcase/approaches/", "site"),
    ("https://github.com/thekaveh/rag-showcase/wiki/Home", "site"),
    ("../README.md", "wiki"),
    ("../README.md#section", "site"),
    ("../other-page.md", "wiki"),
])
def test_is_forbidden_true_cases(target, surface):
    assert is_forbidden(target, surface)


@pytest.mark.parametrize("target, surface", [
    ("https://example.com/unrelated", "site"),
    ("../README.md", "docs"),  # only forbidden on site/wiki, not the repo-tree surface
    ("../other-page.md", "site"),  # the bare "../" wiki-relative guard is wiki-only
    ("approaches.md", "wiki"),
    ("results/evidence.jsonl", "wiki"),
])
def test_is_forbidden_false_cases(target, surface):
    assert not is_forbidden(target, surface)


def test_strip_forbidden_links_keeps_text_drops_target():
    markdown = "See [the repo](https://github.com/thekaveh/rag-showcase) for source."
    out = strip_forbidden_links(markdown, "site")
    assert "the repo" in out
    assert "github.com/thekaveh/rag-showcase" not in out


def test_strip_forbidden_links_preserves_allowed_links_and_images():
    markdown = "![diagram](img/x.png) and [docs](approaches.md)"
    out = strip_forbidden_links(markdown, "site")
    assert out == markdown  # images are never touched; allowed links pass through unchanged
