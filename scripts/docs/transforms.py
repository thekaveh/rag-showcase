from __future__ import annotations

import re
from pathlib import Path, PurePosixPath

from .links import MD_LINK_RE, strip_forbidden_links
from .manifest import DOCS

INCLUDE_RE = re.compile(r"\{%\s*include-markdown\s+\"([^\"]+)\"\s*%\}", re.MULTILINE)
SOURCE_DIRS = {
    "backend_plugins", "compare", "compose", "corpus", "demo", "ingest",
    "n8n", "register", "scripts",
}


def _expand_includes(markdown: str, source: Path) -> str:
    base = (DOCS / source).parent

    def replace(match: re.Match[str]) -> str:
        target = (base / match.group(1)).resolve()
        root = DOCS.parents[0].resolve()
        if not str(target).startswith(str(root)):
            return ""
        if not target.is_file():
            return ""
        return target.read_text(encoding="utf-8").strip() + "\n"

    return INCLUDE_RE.sub(replace, markdown)


def _relative(from_file: PurePosixPath, to_file: str) -> str:
    from_parts = from_file.parent.parts
    to_parts = PurePosixPath(to_file).parts
    i = 0
    while i < len(from_parts) and i < len(to_parts) and from_parts[i] == to_parts[i]:
        i += 1
    up = [".."] * (len(from_parts) - i)
    down = list(to_parts[i:])
    rel = "/".join(up + down)
    return rel or PurePosixPath(to_file).name


def _normalize_target(source: PurePosixPath, target: str) -> str:
    resolved = (source.parent / target).as_posix()
    parts: list[str] = []
    for part in PurePosixPath(resolved).parts:
        if part == "..":
            if parts:
                parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts)


def _diagram_asset_target(source: Path, clean_target: str, surface: str, image: bool) -> str | None:
    if clean_target.startswith("diagrams/img/"):
        name = PurePosixPath(clean_target).name
    elif clean_target.startswith("img/"):
        name = PurePosixPath(clean_target).name
    else:
        return None
    if surface == "wiki":
        return f"img/{name}"
    ext = ".svg" if image else ".png"
    stem = PurePosixPath(name).stem
    return _relative(PurePosixPath(source.as_posix()), f"assets/img/{stem}{ext}")


def _nested_diagram_target(
    link_source: PurePosixPath, clean_target: str, surface: str
) -> str | None:
    prefix = "diagrams/approaches/"
    if not clean_target.startswith(prefix):
        return None
    relative = clean_target.removeprefix("diagrams/")
    destination = (
        f"diagrams/{relative}"
        if surface == "wiki"
        else f"assets/diagrams/{relative}"
    )
    return _relative(link_source, destination)


def _diagram_html_target(source: Path, clean_target: str, surface: str) -> str | None:
    if not clean_target.endswith(".html"):
        return None
    name = PurePosixPath(clean_target).name
    if surface == "wiki":
        return f"diagrams/{name}"
    return _relative(PurePosixPath(source.as_posix()), f"assets/diagrams/{name}")


def rewrite_for_surface(
    markdown: str,
    source: Path,
    surface: str,
    mapping: dict[str, str],
    output_source: Path | None = None,
) -> str:
    markdown = _expand_includes(markdown, source)
    link_source = PurePosixPath((output_source or source).as_posix())

    def replace(match: re.Match[str]) -> str:
        bang, text, target = match.groups()
        clean_target = target.split("#", 1)[0]
        anchor = "#" + target.split("#", 1)[1] if "#" in target else ""
        if surface in {"site", "wiki"}:
            nested_diagram = _nested_diagram_target(
                link_source, clean_target, surface
            )
            if nested_diagram:
                return f"{'!' if bang else ''}[{text}]({nested_diagram}{anchor})"
            diagram_asset = _diagram_asset_target(source, clean_target, surface, bool(bang))
            if diagram_asset:
                return f"{'!' if bang else ''}[{text}]({diagram_asset}{anchor})"
            diagram_html = _diagram_html_target(source, clean_target, surface)
            if diagram_html:
                return f"{'!' if bang else ''}[{text}]({diagram_html}{anchor})"
            if clean_target.rstrip("/") == "results" and "results/README.md" in mapping:
                new_target = _relative(link_source, mapping["results/README.md"]) + anchor
                return f"[{text}]({new_target})"
        if clean_target.endswith(".md"):
            normalized = _normalize_target(PurePosixPath(source.as_posix()), clean_target)
            if normalized in mapping:
                new_target = _relative(link_source, mapping[normalized]) + anchor
                return f"{'!' if bang else ''}[{text}]({new_target})"
            if surface in {"site", "wiki"}:
                return text if not bang else ""
        if surface in {"site", "wiki"} and not re.match(r"^[a-z][a-z0-9+.-]*:", clean_target) and not clean_target.startswith("#"):
            normalized = _normalize_target(PurePosixPath(source.as_posix()), clean_target)
            top = normalized.split("/", 1)[0]
            if top in SOURCE_DIRS or clean_target.endswith((".yaml", ".yml")):
                return text if not bang else ""
        return match.group(0)

    markdown = MD_LINK_RE.sub(replace, markdown)
    return strip_forbidden_links(markdown, surface)
