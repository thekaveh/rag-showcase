# 7.18 Labeled Brand Banner Design

## 1. Objective

Revise the three-surface opener banner so the project name is part of the artwork
and every colored retrieval lane is identified by its selectable RAG alias. Preserve
the existing generated systems artwork and add exact, deterministic typography that
remains readable when GitHub or MkDocs scales the 3600 x 1200 source down.

## 2. Selected Composition

The existing text-free raster remains the visual base. The HTML composition master
adds two typographic layers:

1. `RAG SHOWCASE`, centered in the upper negative space with high-contrast white
   type and a restrained shadow.
2. Seven compact labels positioned directly on the seven colored input streams.

The lane labels use the exact selectable aliases, ordered from top to bottom:

| Lane | Alias | Accent |
|---:|---|---|
| 1 | `vanilla-rag` | cyan |
| 2 | `hybrid-rag` | green |
| 3 | `contextual-rag` | violet |
| 4 | `graph-rag` | amber |
| 5 | `agentic-rag` | blue |
| 6 | `n8n-adaptive-rag` | teal |
| 7 | `lazy-graph-rag` | magenta |

Each alias sits on a near-black translucent backing with a matching left accent.
The backing provides contrast without hiding the lane's direction or introducing a
separate legend that the reader must cross-reference.

## 3. Typography and Geometry

The master remains a fixed 3:1 landscape composition. Text is rendered by the browser
from system fonts, not generated into the raster by an image model. This guarantees
correct spelling and repeatable placement.

- Final PNG: exactly 3600 x 1200 pixels.
- Master coordinate space: 1800 x 600 CSS pixels, rendered at 2x density.
- Project title: centered, uppercase, at least 56 CSS pixels and clear of lane 1.
- Lane labels: monospace, at least 21 CSS pixels, with a minimum 34-pixel backing.
- Labels align to the centerline of their corresponding streams and do not overlap
  one another, the project title, document structures, or the graph convergence.
- Letter spacing is zero. Labels remain single-line at all source dimensions.

The semantic Markdown H1 remains below the image on every surface for accessibility,
navigation, and search. The overlay is brand artwork, not the document's only title.

## 4. Asset and Documentation Contract

`docs/brand/rag-showcase-banner.html` remains the editable composition master and
`docs/brand/rag-showcase-banner.png` remains the canonical published asset. The
generated source art is unchanged. The prompt and asset-role ledger records that the
title and lane labels are deterministic overlays.

README, generated Pages, and generated Wiki continue referencing the same canonical
PNG through their existing surface-specific paths. No documentation source gains an
independent copy or a manually maintained alternate banner.

## 5. Verification

Acceptance requires:

- an automated assertion for the exact project title and all seven aliases in the
  composition master;
- a 3600 x 1200 output assertion;
- visual inspection of the standalone banner at full resolution;
- desktop and narrow-viewport inspection of the rendered documentation opener;
- no overlapping labels, clipped text, or unreadable aliases;
- `make docs-check`, the complete Python suite, Ruff, and sortable-table tests;
- green feature and promotion PRs, followed by live Pages and Wiki verification.
