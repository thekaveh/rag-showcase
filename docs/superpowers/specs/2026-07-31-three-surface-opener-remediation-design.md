# 7.14 Three-Surface Opener and Publishing Remediation Design

## 1. Objective

Resolve every finding from the 2026-07-31 three-surface documentation audit while
preserving the repository's canonical-docs architecture: committed Markdown and
diagram masters remain the source; the MkDocs and GitHub Wiki trees remain generated
and ignored.

## 2. Opening Contract

`README.md` and `docs/index.md` will share four deliberately duplicated, machine-checked
blocks:

1. One exact tagline.
2. One exact 100-150 word executive summary.
3. One exact status-badge row.
4. One exact, category-complete technology line.

Both openers will embed the same committed landscape poster through surface-relative
paths. A small `scripts.docs.opener` module will own the canonical strings, parse
marked blocks, and fail the documentation gate on punctuation, wording, word-count,
badge, technology, or poster drift.

The summary will describe the uniform response *envelope* and available evidence. It
will not imply that LightRAG exposes retrieved contexts when its current response does
not.

## 3. Poster Contract

The poster will be a standalone dark HTML document with one inline landscape SVG,
following the established architecture-diagram design system. The SVG will show the
headline workflow rather than duplicate the detailed architecture map:

1. One question enters through Open WebUI or the evaluation harness.
2. Atlas LiteLLM routes to seven plugin aliases.
3. The approaches fan into vector, graph, agentic, workflow, and lazy-graph paths.
4. Persisted results flow to Ragas and the blinded judge panel.

The existing diagram renderer will derive the site SVG and committed/wiki PNG. The
committed PNG must be landscape and at least 2400 pixels wide.

## 4. Wiki Projection Contract

GitHub Wiki output will be Gollum-native Markdown. The wiki transform will:

- remove leading MkDocs front matter;
- remove MkDocs `markdown` wrapper elements while retaining their contents;
- remove Material button attribute lists;
- emit extensionless page links so navigation stays on rendered wiki pages;
- preserve `.html`, image, JSON, and JSONL artifact links.

The generated-content gate and unit tests will reject MkDocs-only opener syntax and
local wiki page links ending in `.md`.

## 5. Publishing and CI Contract

The documentation workflow will run for every push and pull request targeting
`develop` or `main`; path filtering will not decide whether a claim-bearing source is
important enough to validate. On a `main` push, wiki publication requires
`WIKI_DEPLOY_KEY`. A missing key is an explicit failure, not a successful skip.

The repository will receive a dedicated write-enabled deploy key and the matching
private key will be stored only in the GitHub Actions secret. The final `main` workflow
must publish the generated wiki and the live wiki tree must match a fresh local build.

## 6. Factual Corrections

- The local graph runbook will distinguish LightRAG-dependent `graph-rag` and the
  graph tool in `agentic-rag` from independent `lazy-graph-rag`.
- The architecture master will label lazy-graph persistence as a dedicated JSON cache
  volume, not Supabase, and its PNG will be regenerated.
- The README per-query-winner reference will target dataset report section 5.
- The home-page results call to action will target the canonical sortable leaderboard.

## 7. Verification

Acceptance requires opener parity tests, wiki transformation tests, factual contract
tests, diagram dimensions, deterministic generation, strict MkDocs build, the full
Python suite, Ruff, sortable-table tests, successful PR checks, successful Pages and
wiki publication from `main`, and live-surface comparison.
