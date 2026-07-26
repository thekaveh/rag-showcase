from __future__ import annotations

import os
import re
import shutil
import tempfile
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


def _render_fallback_png(svg: str, png: Path) -> None:
    if png.exists():
        return
    # A unique-per-call path (not a fixed shared name) so two concurrent
    # local `build()` invocations never unlink/overwrite each other's
    # in-flight temp file.
    fd, tmp_name = tempfile.mkstemp(suffix=".svg", dir=ROOT, prefix=".tmp-docs-diagram-")
    os.close(fd)
    tmp_svg = Path(tmp_name)
    tmp_svg.write_text(svg, encoding="utf-8")
    # Render into a unique temp PNG (same directory as the final target, so the
    # publish below is same-filesystem) and atomically publish via os.replace.
    # cairosvg performs multiple internal writes; two concurrent local `build()`
    # invocations both passing the `if png.exists()` check above and rendering
    # straight into the shared final path could otherwise interleave/truncate
    # each other's output — the same class of race pass-28 already fixed for
    # the scratch SVG input above, just not yet closed for this output.
    png.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_png_name = tempfile.mkstemp(
        suffix=".png", dir=png.parent, prefix=f".tmp-{png.stem}-")
    os.close(fd)
    tmp_png = Path(tmp_png_name)
    try:
        svg_to_png(tmp_svg, tmp_png)
        os.replace(tmp_png, png)
    finally:
        tmp_svg.unlink(missing_ok=True)
        tmp_png.unlink(missing_ok=True)


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
        _render_fallback_png(svg, png)
        if site_dir is not None:
            target = site_dir / "assets" / "img" / png.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, target)
        if wiki_dir is not None:
            target = wiki_dir / "img" / png.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(png, target)

    # The seven per-approach diagrams (diagrams/approaches/<name>/data-flow.html)
    # are nested outside html_dir's own top-level glob, so they never got the
    # cairosvg fallback above — only the manual headless-Chrome workflow in
    # docs/architecture.md §6 could regenerate a missing one. build_docs.py's
    # _copy_tree_files already distributes whatever PNG is committed under
    # diagrams/approaches/ into site_dir/wiki_dir wholesale, so this loop only
    # needs to fill in a missing PNG in place; it must not also copy by
    # png.name into the flat site/wiki img/ dirs like the top-level loop does,
    # since all seven share the filename "data-flow.png" and would overwrite
    # each other there.
    for html_path in sorted((html_dir / "approaches").glob("*/data-flow.html")):
        svg = extract_svg(html_path)
        png = html_path.parent / "data-flow.png"
        _render_fallback_png(svg, png)
