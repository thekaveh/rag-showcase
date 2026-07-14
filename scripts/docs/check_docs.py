from __future__ import annotations

import re
import subprocess
import sys

from .build_docs import SITE_SRC, WIKI_SRC, build, check_determinism
from .links import is_forbidden
from .manifest import DOCS, first_h1, iter_pages, load_manifest

PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b")
EMPTY_FENCE_RE = re.compile(r"```[A-Za-z0-9_-]*\n```", re.MULTILINE)


def _fail(message: str) -> None:
    raise SystemExit(message)


def check_manifest_h1() -> None:
    manifest = load_manifest()
    for page in iter_pages(manifest):
        text = (DOCS / page.source).read_text(encoding="utf-8")
        h1 = first_h1(text)
        expected = page.nav_label
        if h1 != expected:
            _fail(f"{page.source}: H1 {h1!r} does not match manifest {expected!r}")


def check_generated_content() -> None:
    for root, surface in [(SITE_SRC, "site"), (WIKI_SRC, "wiki")]:
        for path in root.rglob("*.md"):
            text = path.read_text(encoding="utf-8")
            if PLACEHOLDER_RE.search(text):
                _fail(f"{path}: placeholder marker leaked into generated {surface}")
            if EMPTY_FENCE_RE.search(text):
                _fail(f"{path}: empty fenced code block")
            for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
                if is_forbidden(match.group(1), surface):
                    _fail(f"{path}: forbidden cross-surface link {match.group(1)}")


def check_readme() -> None:
    text = (DOCS.parent / "README.md").read_text(encoding="utf-8")
    if re.search(r"mkdocs|wiki.*sync|github\.io/", text, re.IGNORECASE):
        _fail("README.md leaks docs publishing mechanics")


def main() -> None:
    build()
    check_manifest_h1()
    check_generated_content()
    check_readme()
    check_determinism()
    subprocess.run([sys.executable, "-m", "mkdocs", "build", "--clean", "--strict", "--site-dir", "site"], check=True)


if __name__ == "__main__":
    main()
