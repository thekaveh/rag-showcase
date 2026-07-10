from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
MANIFEST = DOCS / "manifest.yaml"


class ManifestError(RuntimeError):
    """Raised when docs/manifest.yaml is missing, malformed, or inconsistent."""


@dataclass(frozen=True)
class Page:
    number: str
    title: str
    source: Path
    section: str

    @property
    def nav_label(self) -> str:
        return f"{self.number} {self.title}"

    @property
    def wiki_name(self) -> str:
        rel = self.source.with_suffix("")
        return "-".join(rel.parts) + ".md"


def load_manifest(path: Path = MANIFEST) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ManifestError(f"manifest not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ManifestError(f"invalid manifest YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ManifestError("manifest root must be a mapping")
    if not isinstance(raw.get("sections"), list):
        raise ManifestError("manifest must contain a sections list")
    return raw


def iter_pages(manifest: dict[str, Any]) -> list[Page]:
    pages: list[Page] = []
    seen: set[Path] = set()
    for section in manifest["sections"]:
        section_title = section.get("title")
        if not section_title:
            raise ManifestError("every section needs a title")
        section_pages = section.get("pages")
        if not isinstance(section_pages, list):
            raise ManifestError(f"section {section_title!r} needs a pages list")
        for row in section_pages:
            try:
                number = str(row["number"])
                title = str(row["title"])
                source = Path(str(row["source"]))
            except KeyError as exc:
                raise ManifestError(f"page in {section_title!r} missing {exc.args[0]}") from exc
            if source in seen:
                raise ManifestError(f"duplicate manifest source: {source}")
            full = DOCS / source
            if not full.is_file():
                raise ManifestError(f"manifest source missing: {source}")
            seen.add(source)
            pages.append(Page(number=number, title=title, source=source, section=section_title))
    return pages


def source_map(pages: list[Page], surface: str) -> dict[str, str]:
    if surface == "wiki":
        return {page.source.as_posix(): page.wiki_name for page in pages}
    return {page.source.as_posix(): page.source.as_posix() for page in pages}


def first_h1(text: str) -> str | None:
    in_fence = False
    for line in text.splitlines():
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if not in_fence and line.startswith("# "):
            return line[2:].strip()
    return None
