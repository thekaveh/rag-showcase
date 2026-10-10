from __future__ import annotations

import re
from urllib.parse import urlparse

OWNER_REPO_RE = re.compile(r"https?://github\.com/thekaveh/rag-showcase(?:/[^)\s]*)?")
SITE_RE = re.compile(r"https?://thekaveh\.github\.io/rag-showcase/?[^)\s]*")
WIKI_RE = re.compile(r"https?://github\.com/thekaveh/rag-showcase/wiki/?[^)\s]*|/wiki/")
MD_LINK_RE = re.compile(r"(!?)\[([^\]]+)\]\(([^)]+)\)")


def find_links(markdown: str) -> list[tuple[str, str, str]]:
    return [(m.group(1), m.group(2), m.group(3)) for m in MD_LINK_RE.finditer(markdown)]


def is_forbidden(target: str, surface: str) -> bool:
    parsed = urlparse(target)
    if parsed.scheme in {"http", "https"}:
        if OWNER_REPO_RE.search(target):
            return True
        if SITE_RE.search(target):
            return True
        if WIKI_RE.search(target):
            return True
    if surface in {"site", "wiki"} and target.startswith("../README.md"):
        return True
    if surface == "wiki" and target.startswith("../"):
        return True
    return False


def strip_forbidden_links(markdown: str, surface: str) -> str:
    def replace(match: re.Match[str]) -> str:
        bang, text, target = match.groups()
        if bang:
            return match.group(0)
        return text if is_forbidden(target, surface) else match.group(0)

    return MD_LINK_RE.sub(replace, markdown)


def html_anchor_tags(markdown: str) -> list[tuple[int, int, str]]:
    """Locate HTML anchor start tags using a parser, preserving original markup."""
    from html.parser import HTMLParser

    offsets = [0]
    for line in markdown.splitlines(keepends=True):
        offsets.append(offsets[-1] + len(line))

    class Anchors(HTMLParser):
        def __init__(self) -> None:
            super().__init__(convert_charrefs=False)
            self.tags: list[tuple[int, int, str]] = []

        def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
            if tag != 'a':
                return
            href = dict(attrs).get('href')
            if href is not None:
                line, column = self.getpos()
                start = offsets[line - 1] + column
                self.tags.append((start, start + len(self.get_starttag_text()), href))

    parser = Anchors()
    parser.feed(markdown)
    return parser.tags
