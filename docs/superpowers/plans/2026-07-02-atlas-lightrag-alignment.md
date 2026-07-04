# Atlas LightRAG Alignment Implementation Plan

**Status:** Historical artifact — implemented, as-built. Not a live task list.
One post-implementation deviation: a minimal `services.lightrag` section with
optional `*_OLLAMA_LLM_NUM_CTX` context caps was re-added to the overlay
(commit 15c1c8d) because Atlas exposes no public input for them; see
`tests/test_lightrag_overlay.py` for the pinned shape.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update rag-showcase to use Atlas's first-class LightRAG role/query configuration instead of local runtime overrides.

**Architecture:** `scripts/setup-overlay.sh` owns rag-showcase's Atlas `.env` defaults. `compose/rag-overlay.yml` owns only backend plugin mounting and plugin runtime settings. Atlas renders LightRAG role and query settings into its own LightRAG containers.

**Tech Stack:** Bash, Docker Compose, Atlas service manifests, pytest, Markdown docs, GitHub CLI.

## Global Constraints

- Do not assume Mac Studio, Apple Silicon, host Ollama, or any other specific hardware.
- Prefer Atlas public `.env` inputs over LightRAG native runtime env overrides.
- Keep user-edited `infra/.env` values intact on repeated setup runs.
- Keep raw comparison snapshots and generated local result files out of git unless already committed under `docs/results/`.

---

## Task 1: Move LightRAG Role Defaults To Atlas Inputs

**Files:**
- Modify: `scripts/setup-overlay.sh`
- Modify: `compose/rag-overlay.yml`
- Test: `tests/test_lightrag_overlay.py`

**Interfaces:**
- Consumes: Atlas `.env` variables `LIGHTRAG_EXTRACT_LLM_MODEL`, `LIGHTRAG_KEYWORD_LLM_MODEL`, `LIGHTRAG_QUERY_LLM_MODEL`, and `OLLAMA_CUSTOM_MODELS`.
- Produces: a compose overlay that no longer defines `services.lightrag` or `services.lightrag-init`.

- [ ] Add `set_env_default` and `append_csv_env` helpers to `scripts/setup-overlay.sh`.
- [ ] Default `LIGHTRAG_EXTRACT_LLM_MODEL`, `LIGHTRAG_KEYWORD_LLM_MODEL`, and `LIGHTRAG_QUERY_LLM_MODEL` to the configured showcase role model only when unset.
- [ ] Append the default role model to `OLLAMA_CUSTOM_MODELS` without removing user entries.
- [ ] Remove `lightrag` and `lightrag-init` sections from `compose/rag-overlay.yml`.
- [ ] Update `tests/test_lightrag_overlay.py` to assert the overlay delegates LightRAG service config to Atlas.

## Task 2: Refresh Documentation

**Files:**
- Modify: `README.md`
- Modify: `docs/comparison.md`
- Modify: `docs/atlas-reuse-assessment.md`
- Modify: `docs/atlas-lightrag-role-model-spec.md`

**Interfaces:**
- Consumes: Atlas commit `8ce6784`.
- Produces: hardware-neutral docs that mark the Atlas handoff items as resolved.

- [ ] Remove wording that makes host Ollama or Mac hardware sound required.
- [ ] Describe `LLM_PROVIDER_SOURCE=ollama-localhost` as an optional Atlas source.
- [ ] Replace `RAG_LIGHTRAG_*` docs with Atlas `LIGHTRAG_*` variables.
- [ ] Mark the Atlas role-model spec as implemented upstream.

## Task 3: Validate And Publish Metadata

**Files:**
- Modify: GitHub repository About metadata.

**Interfaces:**
- Consumes: `gh repo edit`.
- Produces: hardware-neutral repository description.

- [ ] Run `uv run pytest tests/test_lightrag_overlay.py backend_plugins/rag/tests -q`.
- [ ] Run a full `uv run pytest -q` if the focused suite passes.
- [ ] Inspect `git diff --submodule=log`.
- [ ] Update GitHub About description to describe the repo as an Atlas-based six-approach RAG comparison without hardware assumptions.
