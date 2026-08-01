# 7.16 Brand-First Three-Surface Opener Design

## 1. Objective

Replace the technically correct but visually weak project opening with one deliberate
brand-first experience shared by the repository README, generated documentation site,
and GitHub wiki. Preserve the existing comparison-flow graphic as architecture content,
and restore reliable publication of all three surfaces.

## 2. Selected Direction

Three directions were evaluated:

1. Refine the existing comparison-flow diagram and continue using it as the opener.
2. Use a live Open WebUI screenshot as the banner.
3. Create a dedicated brand banner and move the comparison flow into architecture docs.

Direction 3 is selected. A dense service diagram communicates implementation but does
not create a strong first impression. A screenshot would age quickly and depend on one
runtime configuration. A dedicated banner can communicate seven parallel retrieval
strategies, knowledge structure, and measured comparison without assuming hardware,
models, ports, or a currently running stack.

## 3. Opening Composition

Every surface opens in this order:

1. Full-width, high-resolution brand banner.
2. Centered `RAG Showcase` H1, without a numeric prefix.
3. Centered bold tagline and one supporting sentence.
4. Centered status/license badges.
5. Three centered, category-grouped rows of logo-bearing technology shields.
6. The shared 100-150 word executive summary.
7. Centered Quick Start, Measured Results, and Architecture links.
8. A compact latest-results callout before the first numbered content section.

The canonical opener module owns the exact title, tagline, supporting sentence,
status badges, technology badge groups, and executive summary. README and landing-page
copies remain deliberately duplicated but machine-checked.

## 4. Banner Contract

The banner is an original wide raster composition, not a service diagram. It depicts
seven distinct streams traversing vector, document, and graph-like structures before
converging into a measured comparison surface. It uses the project's near-black,
cyan, emerald, violet, and amber palette, includes no third-party logos, and contains
no generated text. Exact project typography remains outside the artwork so it is crisp
and accessible on every surface.

The generated source artwork, an HTML composition master, the final PNG, and the final
generation prompt are committed under `docs/brand/`. The final PNG is at least 3600
pixels wide with a 3:1 landscape ratio. The build copies it physically into the site
and wiki output trees.

## 5. Technology Badges

Status badges remain separate from technology badges. Technology shields span the
actual showcase runtime by category:

- Platform and API: Atlas, Open WebUI, LiteLLM, FastAPI.
- Retrieval and storage: Weaviate, LightRAG, Neo4j, Supabase/Postgres.
- Processing and evaluation: Chonkie, TEI, n8n, Ollama, Ragas.

Each item renders as an `<img>` shield. Where Simple Icons provides the correct logo,
the shield uses it; custom project labels remain honest rather than borrowing an
unrelated logo.

## 6. Home-Page Heading Contract

The landing page is an explicit exception to numbered content headings. Its manifest
entry keeps global navigation position `1` but declares `display_number: false`.
The manifest parser exposes the resulting heading/nav label, and the H1 checker accepts
the shared centered HTML H1. All non-home pages retain exact numbered H1 enforcement.

## 7. Publication Contract

The existing `develop -> main` promotion PR remains the publication vehicle. Before
promotion, the repository receives one dedicated write-enabled wiki deploy key and the
matching private key is stored only in the `WIKI_DEPLOY_KEY` Actions secret. After the
main merge, Pages and wiki jobs must both succeed, and fresh downloads of both live
surfaces must contain the new banner, centered title, and technology shields.

## 8. Verification

Acceptance requires opener-contract tests, home-heading tests, banner dimensions and
copy tests, native-wiki tests, deterministic generation, strict MkDocs compilation,
the full Python suite, Ruff, sortable-table tests, visual inspection of repository and
site rendering, green feature and promotion PR checks, and live Pages/wiki parity.
