# 7.15 Three-Surface Opener and Publishing Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repair opener consistency, GitHub Wiki generation and publishing, CI coverage, and the factual documentation defects identified by the 2026-07-31 audit.

**Architecture:** Preserve `README.md` and `docs/` as canonical sources and project them through the existing deterministic site/wiki generator. Add a focused opener contract module, wiki-only Markdown cleanup, a new HTML/SVG poster master, and regression tests at each boundary.

**Tech Stack:** Python 3.10+, pytest, MkDocs Material, GitHub Actions, GitHub Wiki/Gollum Markdown, inline SVG, CairoSVG, Ruff.

## Global Constraints

- Generated `generated/`, `site/`, and root `mkdocs.yml` outputs remain ignored.
- README and the landing page carry identical tagline, summary, badges, and technology copy.
- The executive summary contains 100-150 words and does not leak documentation-system mechanics.
- Wiki links between generated pages are extensionless.
- The poster and corrected architecture diagram are regenerated from committed HTML/SVG masters.
- Wiki publication from `main` fails when its deploy key is absent.

---

### Task 1: Lock the Opening Contract

**Files:**
- Create: `scripts/docs/opener.py`
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `scripts/docs/check_docs.py`
- Test: `tests/docs/test_opener.py`

**Interfaces:**
- Produces: `check_canonical_openers() -> None`, called by the documentation gate.
- Consumes: marked `tagline`, `summary`, `badges`, and `powered-by` blocks in both canonical openers.

- [ ] Add failing tests for exact block parity, 100-150 word summary length, required stack categories, poster paths, corrected evidence wording, CTA target, and README section anchor.
- [ ] Run `uv run pytest tests/docs/test_opener.py -q` and confirm the new assertions fail against the audited state.
- [ ] Implement the canonical opener module and update both documents with identical blocks.
- [ ] Run `uv run pytest tests/docs/test_opener.py -q` and confirm it passes.

### Task 2: Add the Shared Poster

**Files:**
- Create: `docs/diagrams/rag-showcase-poster.html`
- Create: `docs/diagrams/img/rag-showcase-poster.png`
- Modify: `tests/docs/test_three_surface_docs.py`

**Interfaces:**
- Produces: one inline SVG master consumed by `scripts.docs.render_diagrams.render_all`.
- Produces: a committed landscape PNG and generated site SVG/wiki PNG.

- [ ] Add a failing diagram-publication test for the poster and its minimum landscape dimensions.
- [ ] Build the self-contained landscape HTML/SVG master.
- [ ] Generate the PNG through the existing renderer and inspect it for clipping or overlap.
- [ ] Run the targeted diagram tests.

### Task 3: Generate Native GitHub Wiki Markdown

**Files:**
- Modify: `scripts/docs/transforms.py`
- Modify: `scripts/docs/check_docs.py`
- Modify: `tests/docs/test_three_surface_docs.py`
- Modify: `tests/docs/test_check_docs.py`

**Interfaces:**
- Produces: wiki output without leading front matter, Markdown wrapper elements, Material button attributes, or `.md` page links.
- Preserves: site transformations and non-page artifact suffixes.

- [ ] Add failing tests for cleaned wiki opener syntax and extensionless page links.
- [ ] Run the targeted tests and confirm the audited output fails.
- [ ] Implement wiki-only cleanup and extensionless mapping.
- [ ] Add generated-content rejection checks for regressions.
- [ ] Run all documentation tests.

### Task 4: Make Publishing and CI Fail Closed

**Files:**
- Modify: `.github/workflows/docs.yml`
- Modify: `tests/docs/test_three_surface_docs.py`

**Interfaces:**
- Produces: unfiltered `main`/`develop` push and pull-request validation.
- Produces: mandatory-key wiki publication on `main`.

- [ ] Add workflow-contract tests that reject path filters and successful missing-key skips.
- [ ] Remove documentation workflow path filters and conditional skip behavior.
- [ ] Require `WIKI_DEPLOY_KEY` before setup, generation, and publication.
- [ ] Configure the repository deploy key and Actions secret without committing private material.

### Task 5: Correct Graph Claims and Diagrams

**Files:**
- Modify: `docs/guide/local-graph-runs.md`
- Modify: `docs/diagrams/architecture-detailed.html`
- Modify: `docs/diagrams/img/architecture-detailed.png`
- Modify: `tests/test_approach_docs.py`

**Interfaces:**
- Produces: graph dependency prose consistent with the lazy-graph implementation.
- Produces: architecture storage labels consistent with `compose/rag-overlay.yml`.

- [ ] Add failing assertions rejecting a LightRAG dependency for lazy graph and a Supabase lazy-cache label.
- [ ] Correct the prose and SVG labels.
- [ ] Regenerate and visually inspect the architecture PNG.
- [ ] Run approach-document tests.

### Task 6: Publish and Verify All Three Surfaces

**Files:**
- Modify: `docs/manifest.yaml`

**Interfaces:**
- Consumes: all prior tasks.
- Produces: numbered navigation for this design and plan, verified generated surfaces, and live Pages/wiki parity.

- [ ] Register design notes 7.14 and 7.15 in the manifest.
- [ ] Run `make docs-check`, strict MkDocs, all Python tests, Ruff, and sortable-table tests.
- [ ] Push the branch, merge its PR into `develop`, then merge a `develop` to `main` promotion PR.
- [ ] Wait for the main documentation workflow and verify Pages and wiki live output against fresh local generation.
- [ ] Delete the feature branch locally and remotely after both promotions are complete.
