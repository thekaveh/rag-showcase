from __future__ import annotations

import re
import shutil
from pathlib import Path

from .manifest import DOCS, ROOT

SVG_RE = re.compile(r"(<svg\b.*?</svg>)", re.DOTALL | re.IGNORECASE)
ENTITY_REPLACEMENTS = {
    "&middot;": "·",
    "&Sigma;": "Σ",
    "&mdash;": "—",
    "&ndash;": "–",
}


def sanitize_svg(svg: str) -> str:
    for entity, value in ENTITY_REPLACEMENTS.items():
        svg = svg.replace(entity, value)
    return svg


def extract_svg(html_path: Path) -> str:
    text = html_path.read_text(encoding="utf-8")
    match = SVG_RE.search(text)
    if not match:
        raise RuntimeError(f"no inline SVG found in {html_path}")
    return sanitize_svg(match.group(1))


def svg_to_png(svg_path: Path, png_path: Path) -> None:
    import cairosvg

    png_path.parent.mkdir(parents=True, exist_ok=True)
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=2400)


def render_all(site_dir: Path | None = None, wiki_dir: Path | None = None) -> None:
    html_dir = DOCS / "diagrams"
    img_dir = html_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    for html_path in sorted(html_dir.glob("*.html")):
        name = html_path.stem
        svg = extract_svg(html_path)
        if site_dir is not None:
            out = site_dir / "assets" / "img" / f"{name}.svg"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(svg, encoding="utf-8")
        png = img_dir / f"{name}.png"
        if not png.exists():
            tmp_svg = ROOT / ".tmp-docs-diagram.svg"
            tmp_svg.write_text(svg, encoding="utf-8")
            try:
                svg_to_png(tmp_svg, png)
            finally:
                tmp_svg.unlink(missing_ok=True)
        if site_dir is not None:
            target = site_dir / "assets" / "img" / png.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, target)
        if wiki_dir is not None:
            target = wiki_dir / "img" / png.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, target)
