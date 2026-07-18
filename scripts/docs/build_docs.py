from __future__ import annotations

import argparse
import filecmp
import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Any

import yaml

from .manifest import DOCS, ROOT, Page, iter_pages, load_manifest, source_map
from .render_diagrams import render_all
from .transforms import rewrite_for_surface

GENERATED = ROOT / "generated"
SITE_SRC = GENERATED / "site"
WIKI_SRC = GENERATED / "wiki"
MKDOCS = ROOT / "mkdocs.yml"


def _clean(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _copy_tree_files(src: Path, dst: Path, pattern: str = "*") -> None:
    if not src.exists():
        return
    for path in src.rglob(pattern):
        if path.is_file():
            rel = path.relative_to(src)
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)


def _page_text(page: Page, surface: str, mapping: dict[str, str]) -> str:
    raw = (DOCS / page.source).read_text(encoding="utf-8")
    output_source = page.source
    if surface == "wiki":
        output_source = Path("Home.md" if page.source.as_posix() == "index.md" else page.wiki_name)
    return rewrite_for_surface(raw, page.source, surface, mapping, output_source=output_source).rstrip() + "\n"


def render_site(manifest: dict[str, Any], pages: list[Page], site_dir: Path = SITE_SRC) -> None:
    _clean(site_dir)
    mapping = source_map(pages, "site")
    for page in pages:
        _write(site_dir / page.source, _page_text(page, "site", mapping))
    _copy_tree_files(DOCS / "stylesheets", site_dir / "stylesheets")
    _copy_tree_files(DOCS / "javascripts", site_dir / "javascripts", "*.js")
    _copy_tree_files(DOCS / "results", site_dir / "results", "*.json")
    _copy_tree_files(DOCS / "results", site_dir / "results", "*.jsonl")
    _copy_tree_files(
        DOCS / "diagrams" / "approaches",
        site_dir / "assets" / "diagrams" / "approaches",
    )
    for html in (DOCS / "diagrams").glob("*.html"):
        target = site_dir / "assets" / "diagrams" / html.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(html, target)
    render_all(site_dir=site_dir)


def _wiki_sidebar(manifest: dict[str, Any], pages: list[Page]) -> str:
    by_source = {page.source.as_posix(): page for page in pages}
    lines = ["# RAG Showcase", ""]
    for section in manifest["sections"]:
        lines.append(f"## {section['title']}")
        for row in section["pages"]:
            page = by_source[row["source"]]
            target = "Home" if page.source.as_posix() == "index.md" else page.wiki_name[:-3]
            lines.append(f"- [{page.nav_label}]({target})")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_wiki(manifest: dict[str, Any], pages: list[Page], wiki_dir: Path = WIKI_SRC) -> None:
    _clean(wiki_dir)
    mapping = source_map(pages, "wiki")
    for page in pages:
        text = _page_text(page, "wiki", mapping)
        name = "Home.md" if page.source.as_posix() == "index.md" else page.wiki_name
        _write(wiki_dir / name, text)
    _write(wiki_dir / "_Sidebar.md", _wiki_sidebar(manifest, pages))
    _write(wiki_dir / "_Footer.md", "Generated from the canonical rag-showcase docs.\n")
    _copy_tree_files(DOCS / "results", wiki_dir / "results", "*.json")
    _copy_tree_files(DOCS / "results", wiki_dir / "results", "*.jsonl")
    _copy_tree_files(
        DOCS / "diagrams" / "approaches",
        wiki_dir / "diagrams" / "approaches",
    )
    for html in (DOCS / "diagrams").glob("*.html"):
        target = wiki_dir / "diagrams" / html.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(html, target)
    render_all(wiki_dir=wiki_dir)


def _nav(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    nav: list[dict[str, Any]] = []
    for section in manifest["sections"]:
        rows = []
        for page in section["pages"]:
            rows.append({f"{page['number']} {page['title']}": page["source"]})
        nav.append({section["title"]: rows})
    return nav


def render_mkdocs_yml(manifest: dict[str, Any], path: Path = MKDOCS) -> None:
    data: dict[str, Any] = {
        "site_name": manifest["site_name"],
        "site_description": manifest.get("site_description", ""),
        "site_url": "https://thekaveh.github.io/rag-showcase/",
        "site_author": "Kaveh Razavi",
        "copyright": "Copyright © 2026 Kaveh Razavi",
        "docs_dir": "generated/site",
        "use_directory_urls": False,
        "theme": {
            "name": "material",
            "language": "en",
            "font": {"text": "Inter", "code": "JetBrains Mono"},
            "palette": [
                {"scheme": "slate", "primary": "black", "accent": "cyan",
                 "toggle": {"icon": "material/weather-sunny", "name": "Switch to light mode"}},
                {"scheme": "default", "primary": "white", "accent": "cyan",
                 "toggle": {"icon": "material/weather-night", "name": "Switch to dark mode"}},
            ],
            "features": [
                "navigation.tabs", "navigation.tabs.sticky", "navigation.sections",
                "navigation.top", "navigation.indexes", "navigation.footer",
                "toc.follow", "search.suggest", "search.highlight", "search.share",
                "content.code.copy", "content.tooltips",
            ],
        },
        "plugins": ["search"],
        "markdown_extensions": [
            "abbr", "admonition", "attr_list", "def_list", "footnotes",
            "md_in_html", "tables",
            {"toc": {"permalink": True}},
            "pymdownx.details", {"pymdownx.highlight": {"anchor_linenums": True}},
            "pymdownx.inlinehilite", "pymdownx.snippets",
            {"pymdownx.superfences": {"custom_fences": [
                {"name": "mermaid", "class": "mermaid",
                 "format": "!!python/name:pymdownx.superfences.fence_code_format"}
            ]}},
            {"pymdownx.tabbed": {"alternate_style": True}},
            {"pymdownx.emoji": {
                "emoji_index": "!!python/name:material.extensions.emoji.twemoji",
                "emoji_generator": "!!python/name:material.extensions.emoji.to_svg",
            }},
        ],
        "extra_css": ["stylesheets/extra.css"],
        "extra_javascript": ["javascripts/sortable-tables.js"],
        "nav": _nav(manifest),
    }
    text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True, width=1000)
    text = text.replace("'!!python/name:pymdownx.superfences.fence_code_format'", "!!python/name:pymdownx.superfences.fence_code_format")
    text = text.replace("'!!python/name:material.extensions.emoji.twemoji'", "!!python/name:material.extensions.emoji.twemoji")
    text = text.replace("'!!python/name:material.extensions.emoji.to_svg'", "!!python/name:material.extensions.emoji.to_svg")
    _write(path, text)


def _hash_tree(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for file in sorted(p for p in path.rglob("*") if p.is_file()):
        out[file.relative_to(path).as_posix()] = hashlib.sha256(file.read_bytes()).hexdigest()
    return out


def assert_dirs_equal(a: Path, b: Path) -> None:
    if _hash_tree(a) != _hash_tree(b):
        diff = filecmp.dircmp(a, b)
        raise AssertionError(f"generated docs are not deterministic: {diff.left_only=} {diff.right_only=} {diff.diff_files=}")


def build(site: bool = True, wiki: bool = True, mkdocs: bool = True) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    if site:
        render_site(manifest, pages)
    if wiki:
        render_wiki(manifest, pages)
    if mkdocs:
        render_mkdocs_yml(manifest)


def check_determinism() -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    with tempfile.TemporaryDirectory() as td:
        first = Path(td) / "first"
        second = Path(td) / "second"
        render_site(manifest, pages, first / "site")
        render_wiki(manifest, pages, first / "wiki")
        render_site(manifest, pages, second / "site")
        render_wiki(manifest, pages, second / "wiki")
        assert_dirs_equal(first, second)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build generated docs surfaces.")
    parser.add_argument("--site", action="store_true", help="Render generated/site")
    parser.add_argument("--wiki", action="store_true", help="Render generated/wiki")
    parser.add_argument("--mkdocs", action="store_true", help="Render root mkdocs.yml")
    parser.add_argument("--check", action="store_true", help="Check deterministic generation")
    args = parser.parse_args()
    if args.check:
        check_determinism()
        return
    requested = args.site or args.wiki or args.mkdocs
    build(
        site=args.site or not requested,
        wiki=args.wiki or not requested,
        mkdocs=args.mkdocs or not requested,
    )


if __name__ == "__main__":
    main()
