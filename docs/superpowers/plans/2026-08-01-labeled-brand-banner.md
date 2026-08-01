# 7.19 Labeled Brand Banner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overlay the RAG Showcase title and the seven exact selectable approach aliases on their corresponding colored lanes in the canonical three-surface banner.

**Architecture:** Keep the generated raster as immutable source art and make the existing HTML master solely responsible for exact typography and placement. Render that master at 2x density into the same canonical PNG already copied and rewritten by the documentation pipeline.

**Tech Stack:** HTML/CSS, Playwright with system Chrome, PNG, pytest, MkDocs Material, GitHub Actions.

## Global Constraints

- Preserve the exact 3600 x 1200 final dimensions and 3:1 aspect ratio.
- Use the exact aliases `vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`, `n8n-adaptive-rag`, and `lazy-graph-rag` from top to bottom.
- Render `RAG SHOWCASE` in the upper negative space while retaining the semantic Markdown H1 below the image.
- Keep all labels single-line, readable, unclipped, non-overlapping, and tied directly to their corresponding lane.
- Leave the original generated source artwork unchanged.

---

### Task 1: Lock the Typography Contract

**Files:**
- Modify: `tests/docs/test_three_surface_docs.py`
- Consume: `docs/brand/rag-showcase-banner.html`

**Interfaces:**
- Consumes: the committed HTML composition master.
- Produces: an automated contract for one overlay title, seven unique lane labels, lane ordering, and minimum typography sizes.

- [ ] **Step 1: Write the failing test**

```python
def test_brand_banner_master_labels_every_retrieval_lane() -> None:
    html = (DOCS / "brand" / "rag-showcase-banner.html").read_text(encoding="utf-8")
    assert '<h1 class="banner__title">RAG SHOWCASE</h1>' in html
    aliases = ["vanilla-rag", "hybrid-rag", "contextual-rag", "graph-rag",
               "agentic-rag", "n8n-adaptive-rag", "lazy-graph-rag"]
    positions = [html.index(f">{alias}</span>") for alias in aliases]
    assert positions == sorted(positions)
    assert html.count('class="lane-label ') == 7
    assert "font-size: 56px" in html
    assert "font-size: 21px" in html
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/docs/test_three_surface_docs.py::test_brand_banner_master_labels_every_retrieval_lane -q`

Expected: fail because the current master contains no overlay title or lane labels.

- [ ] **Step 3: Commit the failing contract with the implementation task**

Do not commit a permanently red revision. Continue directly to Task 2 and commit the red/green pair together.

### Task 2: Compose and Render the Labeled Banner

**Files:**
- Modify: `docs/brand/rag-showcase-banner.html`
- Modify: `docs/brand/rag-showcase-banner.png`
- Modify: `docs/brand/rag-showcase-banner-prompt.md`
- Test: `tests/docs/test_three_surface_docs.py`

**Interfaces:**
- Consumes: `rag-showcase-banner-art.png` and the title/alias contract from Task 1.
- Produces: the deterministic 1800 x 600 CSS master and 3600 x 1200 canonical PNG.

- [ ] **Step 1: Add deterministic overlays**

Use one absolute title and seven absolute labels inside `.banner`:

```html
<h1 class="banner__title">RAG SHOWCASE</h1>
<div class="lane-labels" aria-label="RAG approaches">
  <span class="lane-label lane-label--vanilla">vanilla-rag</span>
  <span class="lane-label lane-label--hybrid">hybrid-rag</span>
  <span class="lane-label lane-label--contextual">contextual-rag</span>
  <span class="lane-label lane-label--graph">graph-rag</span>
  <span class="lane-label lane-label--agentic">agentic-rag</span>
  <span class="lane-label lane-label--adaptive">n8n-adaptive-rag</span>
  <span class="lane-label lane-label--lazy">lazy-graph-rag</span>
</div>
```

Use a 56px system sans-serif title and 21px system monospace lane labels. Position
labels at the stream centerlines and give each a near-black translucent background
plus a matching colored left border. Keep `letter-spacing: 0`.

- [ ] **Step 2: Verify GREEN at the source level**

Run: `uv run pytest tests/docs/test_three_surface_docs.py::test_brand_banner_master_labels_every_retrieval_lane -q`

Expected: `1 passed`.

- [ ] **Step 3: Render the canonical PNG**

```bash
python3 -c 'from pathlib import Path; from playwright.sync_api import sync_playwright; p=sync_playwright().start(); b=p.chromium.launch(channel="chrome"); page=b.new_page(viewport={"width":1800,"height":600}, device_scale_factor=2); page.goto(Path("docs/brand/rag-showcase-banner.html").resolve().as_uri()); page.screenshot(path="docs/brand/rag-showcase-banner.png"); b.close(); p.stop()'
```

- [ ] **Step 4: Update the asset ledger**

State that the source art is image-generated and text-free, while the project title
and exact lane aliases are browser-rendered overlays owned by the HTML master.

- [ ] **Step 5: Verify dimensions and visual quality**

Run `sips -g pixelWidth -g pixelHeight docs/brand/rag-showcase-banner.png`; expect
`3600` and `1200`. Inspect the full-resolution banner and rendered docs at 1440 x 1200
and 390 x 844. Reject clipped text, collisions, or unreadable labels.

- [ ] **Step 6: Commit**

```bash
git add docs/brand tests/docs/test_three_surface_docs.py
git commit -m "docs: label the RAG approach banner"
```

### Task 3: Verify and Publish All Three Surfaces

**Files:**
- Consume: `README.md`
- Consume: `docs/index.md`
- Consume: `.github/workflows/docs.yml`

**Interfaces:**
- Consumes: the canonical labeled PNG from Task 2.
- Produces: synchronized repository, Pages, and Wiki openers.

- [ ] **Step 1: Run repository verification**

Run:

```bash
make docs-check
uv run pytest tests backend_plugins/rag/tests -q
uv run ruff check .
make sortable-tables-test
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 2: Push and merge through GitFlow**

Push `codex/labeled-brand-banner`, open a PR into `develop`, wait for green checks,
merge and delete the feature branch, then open or update a `develop -> main` PR,
wait for green checks, and merge it.

- [ ] **Step 3: Verify publication and cleanup**

Require the main workflow's build, Pages, and Wiki jobs to pass. Confirm the live
Pages banner asset returns HTTP 200 and a fresh wiki clone exactly matches
`generated/wiki`. Synchronize local `main` and `develop`; leave no open PR, feature
branch, or extra worktree.
