"""docs_hooks rewrites in-repo source links to GitHub for the published site —
a regex regression silently 404s the site's source references, so pin the
representative shapes."""
from __future__ import annotations

import pytest

import docs_hooks


@pytest.mark.parametrize("markdown, expected", [
    # source FILE one level up -> blob URL
    ("[judge.py](../compare/judge.py)",
     "[judge.py](https://github.com/thekaveh/rag-showcase/blob/main/compare/judge.py)"),
    # source DIRECTORY (trailing slash) two levels up -> tree URL
    ("[corpus](../../corpus/graph_native/)",
     "[corpus](https://github.com/thekaveh/rag-showcase/tree/main/corpus/graph_native/)"),
    # root README special case, anchor preserved
    ("[readme](../README.md#4-the-six-approaches)",
     "[readme](https://github.com/thekaveh/rag-showcase/blob/main/README.md#4-the-six-approaches)"),
    # sibling doc page: NOT a source dir -> untouched for MkDocs to resolve
    ("[approaches](../approaches.md)", "[approaches](../approaches.md)"),
    # non-escaping relative link -> untouched
    ("[local](stylesheets/extra.css)", "[local](stylesheets/extra.css)"),
    # infra/ deliberately excluded (submodule gitlink, not browsable)
    ("[infra](../infra/docker-compose.yml)", "[infra](../infra/docker-compose.yml)"),
    # anchor on a source file link
    ("[cfg](../compose/rag-overlay.yml#L5)",
     "[cfg](https://github.com/thekaveh/rag-showcase/blob/main/compose/rag-overlay.yml#L5)"),
])
def test_on_page_markdown_rewrites(markdown: str, expected: str) -> None:
    assert docs_hooks.on_page_markdown(markdown) == expected


def test_multiple_links_in_one_page() -> None:
    src = "see [a](../demo/queries.yaml) and [b](../evaluation-methodology.md)"
    out = docs_hooks.on_page_markdown(src)
    assert "blob/main/demo/queries.yaml" in out
    assert "(../evaluation-methodology.md)" in out  # doc link untouched
