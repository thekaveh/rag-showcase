"""MkDocs hook: rewrite in-repo source links to GitHub.

The documentation cross-links to source files and directories that live *outside*
the built site — e.g. ``[judge.py](../compare/judge.py)``,
``[queries](../demo/queries.yaml)``, ``[corpus](../corpus/graph_native/)``. Those
targets are not pages, so on the published site they would 404. This hook rewrites
any relative link that escapes ``docs/`` (one or more ``../``) into a top-level
repository source directory to an absolute GitHub URL on the default branch, so the
references resolve for site readers while the docs stay unedited (single source of
truth). ``.md`` links and same-directory asset links are left untouched for MkDocs
to resolve normally.
"""
from __future__ import annotations

import re

_BLOB = "https://github.com/thekaveh/rag-showcase/blob/main/"
_TREE = "https://github.com/thekaveh/rag-showcase/tree/main/"

# Top-level repo source dirs the docs reference. `infra/` is intentionally excluded
# (it is a submodule gitlink on GitHub, not browsable files).
_SRC_DIRS = {
    "backend_plugins", "compare", "corpus", "demo", "ingest",
    "register", "scripts", "n8n", "compose", "brand",
}

# ](  one-or-more ../   path (no ) # or space)   optional #anchor   )
_LINK_RE = re.compile(r"(\]\()((?:\.\./)+)([^)#\s]+)(#[^)]*)?(\))")


def _replace(match: "re.Match[str]") -> str:
    open_paren, _updots, path, anchor, close_paren = match.groups()
    top = path.split("/", 1)[0]
    # The root README lives outside the site; point its references at GitHub. (Only
    # docs-root pages write `../README.md`; nested pages use `../<doc>.md` siblings,
    # which never equal "README.md", so this can't mis-fire on in-site links.)
    if path == "README.md":
        return f"{open_paren}{_BLOB}README.md{anchor or ''}{close_paren}"
    if top not in _SRC_DIRS:
        return match.group(0)  # e.g. ../approaches.md — let MkDocs resolve it
    base = _TREE if path.endswith("/") else _BLOB
    return f"{open_paren}{base}{path}{anchor or ''}{close_paren}"


def on_page_markdown(markdown: str, **kwargs) -> str:
    return _LINK_RE.sub(_replace, markdown)
