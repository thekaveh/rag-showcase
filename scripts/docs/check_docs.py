from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

from .build_docs import SITE_SRC, WIKI_SRC, build, check_determinism
from .links import is_forbidden
from .manifest import DOCS, first_h1, iter_pages, load_manifest
from .opener import OpenerError, check_canonical_openers

PLACEHOLDER_RE = re.compile(r"\b(TODO|TBD|FIXME|XXX)\b")
EMPTY_FENCE_RE = re.compile(r"```[A-Za-z0-9_-]*\n```", re.MULTILINE)
WIKI_MKDOCS_RE = re.compile(
    r"\A---\s*\n|<div\b[^>]*\bmarkdown\b|\{\s*\.md-button",
    re.MULTILINE,
)


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
            if surface == "wiki" and WIKI_MKDOCS_RE.search(text):
                _fail(f"{path}: MkDocs-only syntax leaked into generated wiki")
            for match in re.finditer(r"\[[^\]]+\]\(([^)]+)\)", text):
                target = match.group(1)
                if is_forbidden(target, surface):
                    _fail(f"{path}: forbidden cross-surface link {target}")
                parsed = urlparse(target)
                if (
                    surface == "wiki"
                    and not parsed.scheme
                    and not parsed.netloc
                    and parsed.path.endswith(".md")
                ):
                    _fail(f"{path}: raw wiki page link {target}")


def check_local_links(root: Path) -> None:
    """Reject generated Markdown links whose local file target is absent."""
    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        for match in re.finditer(r"!?\[[^\]]+\]\(([^)]+)\)", text):
            target = match.group(1).strip()
            parsed = urlparse(target)
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            clean = unquote(parsed.path)
            candidate = root / clean.lstrip("/") if clean.startswith("/") else path.parent / clean
            candidates = [candidate]
            if not candidate.suffix:
                candidates.extend([candidate.with_suffix(".md"), candidate / "index.md"])
            if not any(item.exists() for item in candidates):
                _fail(f"{path}: missing local link target {target}")


def check_readme() -> None:
    text = (DOCS.parent / "README.md").read_text(encoding="utf-8")
    if re.search(r"mkdocs|wiki.*sync|github\.io/", text, re.IGNORECASE):
        _fail("README.md leaks docs publishing mechanics")


def check_openers() -> None:
    try:
        check_canonical_openers(DOCS.parent)
    except OpenerError as exc:
        _fail(str(exc))


def main() -> None:
    build()
    check_manifest_h1()
    check_generated_content()
    check_local_links(SITE_SRC)
    check_local_links(WIKI_SRC)
    check_readme()
    check_openers()
    check_determinism()
    subprocess.run(
        [sys.executable, "-m", "mkdocs", "build", "--clean", "--strict", "--site-dir", "site"],
        check=True, timeout=300,
    )


if __name__ == "__main__":
    main()
