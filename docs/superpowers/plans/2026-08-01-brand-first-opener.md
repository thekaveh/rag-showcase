# 7.17 Brand-First Three-Surface Opener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a polished, brand-first opener with a real banner, centered hierarchy, comprehensive technology shields, and synchronized repository, Pages, and wiki surfaces.

**Architecture:** Preserve canonical Markdown and generated site/wiki trees. Add a committed brand-asset family copied by the existing documentation generator, strengthen the canonical opener contract, and make the home-page manifest entry explicitly unnumbered while leaving every content page numbered.

**Tech Stack:** Markdown/HTML, shields.io, Python 3.10+, pytest, MkDocs Material, GitHub Actions, headless Chrome, built-in image generation.

## Global Constraints

- The opener must remain self-contained on each surface.
- The title, tagline, supporting sentence, status badges, technology badges, and summary must have exact cross-source parity.
- The banner must be a committed 3:1 PNG at least 3600 pixels wide.
- The existing comparison-flow asset remains available from architecture documentation.
- Generated trees and root `mkdocs.yml` remain ignored.
- No runtime hardware, model, provider, or port is assumed by the banner.

---

### Task 1: Lock the Branded Opener Contract

**Files:**
- Modify: `scripts/docs/opener.py`
- Modify: `tests/docs/test_opener.py`
- Modify: `README.md`
- Modify: `docs/index.md`

**Interfaces:**
- Produces: canonical `title`, `tagline`, `support`, `badges`, `tech-badges`, and `summary` blocks.
- Consumes: surface-relative banner and CTA targets.

- [ ] Add failing tests requiring centered HTML title/tagline/support, poster-first ordering, three technology-shield groups, at least thirteen technology `<img>` tags, compact actions, and a concise result callout.
- [ ] Run `uv run pytest tests/docs/test_opener.py -q` and confirm failures against the audited opener.
- [ ] Update canonical constants and both opener sources with the approved composition.
- [ ] Run the targeted opener tests and confirm they pass.

### Task 2: Create and Publish the Brand Banner

**Files:**
- Create: `docs/brand/rag-showcase-banner-art.png`
- Create: `docs/brand/rag-showcase-banner.html`
- Create: `docs/brand/rag-showcase-banner.png`
- Create: `docs/brand/rag-showcase-banner-prompt.md`
- Modify: `scripts/docs/build_docs.py`
- Modify: `scripts/docs/transforms.py`
- Modify: `tests/docs/test_three_surface_docs.py`

**Interfaces:**
- Produces: one final banner at `docs/brand/rag-showcase-banner.png` and physical site/wiki copies.
- Consumes: the approved generated-art prompt and headless-Chrome composition master.

- [ ] Add a failing test for canonical dimensions, site/wiki copies, and rewritten local links.
- [ ] Generate the text-free source art with the built-in image-generation tool and record the exact prompt.
- [ ] Compose and render the 3:1 final banner with exact crop and accessible alt text.
- [ ] Add brand-asset copying and surface-specific link rewriting.
- [ ] Run targeted generation tests and visually inspect the final PNG and generated site opener.

### Task 3: Make the Landing Title Deliberately Unnumbered

**Files:**
- Modify: `docs/manifest.yaml`
- Modify: `scripts/docs/manifest.py`
- Modify: `scripts/docs/build_docs.py`
- Modify: `tests/docs/test_three_surface_docs.py`
- Modify: `tests/docs/test_check_docs.py`

**Interfaces:**
- Produces: `Page.display_number: bool` and `Page.nav_label` without a number for home.
- Preserves: exact numbered H1 checks for every non-home page.

- [ ] Add failing tests for HTML-H1 parsing, unnumbered home navigation, and numbered content-page enforcement.
- [ ] Implement optional `display_number: false` parsing and HTML-H1 recognition.
- [ ] Make generated navigation consume `Page.nav_label`.
- [ ] Run manifest and strict-build tests.

### Task 4: Reclassify the Comparison Flow

**Files:**
- Rename: `docs/diagrams/rag-showcase-poster.html` to `docs/diagrams/rag-showcase-comparison-overview.html`
- Rename: `docs/diagrams/img/rag-showcase-poster.png` to `docs/diagrams/img/rag-showcase-comparison-overview.png`
- Modify: `docs/architecture.md`
- Modify: `tests/test_approach_docs.py`

**Interfaces:**
- Produces: an architecture overview flow with no opener role.
- Consumes: existing verified SVG and PNG content without changing its technical claims.

- [ ] Add failing assertions that the architecture page embeds the renamed comparison overview and neither opener references it.
- [ ] Rename the master/PNG and update architecture documentation and regeneration commands.
- [ ] Regenerate/verify generated assets and run approach-document tests.

### Task 5: Configure and Verify Three-Surface Publication

**Files:**
- Consume: `.github/workflows/docs.yml`
- Consume: `scripts/docs/push_wiki.py`

**Interfaces:**
- Produces: write-enabled repository deploy key plus `WIKI_DEPLOY_KEY` Actions secret.
- Produces: live Pages and wiki trees matching canonical generation.

- [ ] Generate a dedicated Ed25519 deploy key; add only the public key to the repository and private key to the Actions secret.
- [ ] Run `make docs-check`, `uv run pytest tests backend_plugins/rag/tests -q`, `uv run ruff check .`, and `make sortable-tables-test`.
- [ ] Push the feature branch, merge its green PR into `develop`, and allow promotion PR `#108` to rerun.
- [ ] Merge the green `develop -> main` promotion PR.
- [ ] Verify successful Pages and wiki jobs and compare live outputs with fresh local generation.
- [ ] Delete the feature branch locally and remotely and confirm a clean two-branch GitFlow state.
