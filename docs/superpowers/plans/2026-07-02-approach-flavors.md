# Approach Flavors Implementation Plan

**Status:** Historical artifact — implemented, as-built. Not a live task list.
One interface deviation: flavor aliases do NOT get per-alias routes
(Task 2 sketched `/graph-rag-wide/v1/chat/completions`); as built, LiteLLM
registers each alias against its BASE route and the handler resolves the
flavor from the request `model` (`flavors.get_for_base`). See
`docs/approach-flavor-tuning.md` for the living description.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reproducible named tuning flavors for each RAG approach, usable from both the automated comparison harness and OpenWebUI model aliases, while preserving the six canonical default endpoints.

**Architecture:** Keep the existing approach endpoints as stable defaults. Add a small flavor configuration layer that maps named aliases such as `graph-rag-wide` to a base approach plus query-time or index-time parameter overrides. The backend resolves those aliases before executing the existing approach implementation; the comparison harness records flavor metadata and can run dataset-ladder comparisons across selected flavors.

**Tech Stack:** Python 3, FastAPI plugin routes, LiteLLM/OpenAI-compatible model aliases, YAML config, pytest, Atlas RAG overlay, Weaviate, LightRAG, n8n.

## Global Constraints

- Keep default behavior unchanged for `vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`, and `n8n-adaptive-rag`.
- Do not assume a particular hardware target; model/provider choices stay configurable through existing Atlas and rag-showcase settings.
- Expose only named, reproducible flavor profiles to OpenWebUI; do not require users to pass hidden ad hoc JSON in chat prompts.
- Distinguish query-time flavors from index-time flavors so the dataset ladder only cold-rebuilds when necessary.
- Keep documentation synchronized with the actual tunable variables and measured result schema.

---

## Files

- Create `compare/flavors.yaml`: canonical experiment flavor manifest.
- Create `compare/flavors.py`: host-side loader for the harness.
- Create `backend_plugins/rag/flavors.yaml`: runtime flavor manifest mounted into the backend.
- Create `backend_plugins/rag/common/flavors.py`: backend loader and request-context override helpers.
- Modify `backend_plugins/rag/common/vectors.py`: accept hybrid alpha and rerank switches as call parameters with default-preserving behavior.
- Modify `backend_plugins/rag/common/lightrag.py`: accept query options instead of only reading process env.
- Modify `backend_plugins/rag/approaches/*.py`: route default endpoints and flavor aliases through shared implementation helpers.
- Modify `compare/run_matrix.py`: add `--flavors`/env support and record base approach + flavor in result cells.
- Modify `scripts/run-dataset-ladder.py`: pass flavor selection through matrix runs and include flavor metadata in snapshots.
- Modify `compare/report_datasets.py`: include flavor-aware summaries when present.
- Modify docs: `README.md`, `docs/approaches.md`, `docs/comparison.md`, and new `docs/approach-flavor-tuning.md`.
- Add tests under `backend_plugins/rag/tests/` and `tests/`.

## Task 1: Flavor Manifest Loading

**Files:**
- Create: `backend_plugins/rag/common/flavors.py`
- Create: `backend_plugins/rag/flavors.yaml`
- Test: `backend_plugins/rag/tests/test_flavors.py`

**Interfaces:**
- Produces `FlavorProfile` dataclass with `alias`, `base`, `label`, `description`, `requires_reingest`, and `params`.
- Produces `get(alias_or_base: str) -> FlavorProfile`.
- Produces `aliases_for_base(base: str) -> list[str]`.

- [ ] Write failing tests for default fallback and alias resolution.
- [ ] Run `uv run pytest backend_plugins/rag/tests/test_flavors.py -q` and verify failures.
- [ ] Implement manifest loader with `RAG_FLAVORS_FILE` override and in-process cache.
- [ ] Add default `backend_plugins/rag/flavors.yaml`.
- [ ] Run focused tests and full plugin tests.

## Task 2: Backend Parameter Plumbing

**Files:**
- Modify: `backend_plugins/rag/common/vectors.py`
- Modify: `backend_plugins/rag/common/lightrag.py`
- Modify: `backend_plugins/rag/approaches/vanilla.py`
- Modify: `backend_plugins/rag/approaches/hybrid.py`
- Modify: `backend_plugins/rag/approaches/contextual.py`
- Modify: `backend_plugins/rag/approaches/graph.py`
- Modify: `backend_plugins/rag/approaches/agentic.py`
- Test: existing approach tests plus new flavor-specific tests.

**Interfaces:**
- Each approach keeps its canonical route.
- Flavor aliases add routes such as `/graph-rag-wide/v1/chat/completions`.
- Backend response `model` value remains the invoked alias.
- Defaults remain byte-for-byte equivalent in practical behavior.

- [ ] Write failing tests for `graph-rag-wide`, `hybrid-rag-high-recall`, and `agentic-rag-deeper` route behavior.
- [ ] Run focused tests and verify failures.
- [ ] Refactor each approach into a small helper that accepts a `FlavorProfile`.
- [ ] Register alias routes from the manifest.
- [ ] Run focused tests and full plugin tests.

## Task 3: Harness Flavor Support

**Files:**
- Create: `compare/flavors.py`
- Create: `compare/flavors.yaml`
- Modify: `compare/run_matrix.py`
- Modify: `scripts/run-dataset-ladder.py`
- Test: `tests/test_flavor_manifest.py`, `tests/test_run_matrix_flavors.py`, `tests/test_dataset_ladder_runner.py`

**Interfaces:**
- `MATRIX_FLAVORS` selects aliases/flavors to run.
- `MATRIX_MODELS` continues to work for existing approach selection.
- Matrix cells include `model`, `base_model`, `flavor`, and `requires_reingest`.
- Dataset ladder can run query-time-only flavor sweeps without unnecessary cold reset.

- [ ] Write failing tests for matrix model expansion and cell metadata.
- [ ] Run focused tests and verify failures.
- [ ] Implement host-side manifest loader and matrix expansion.
- [ ] Thread flavor metadata into dataset ladder snapshots.
- [ ] Run focused tests and full test suite.

## Task 4: Docs And User Invocation

**Files:**
- Create: `docs/approach-flavor-tuning.md`
- Modify: `README.md`
- Modify: `docs/approaches.md`
- Modify: `docs/comparison.md`

**Interfaces:**
- README explains OpenWebUI invocation via named aliases.
- Flavor tuning doc lists every supported profile, parameters, and whether re-ingest is required.
- Approach docs distinguish canonical defaults from experimental flavors.

- [ ] Write/update docs tests so every flavor alias is documented.
- [ ] Run docs tests and verify failures.
- [ ] Add documentation sections and links.
- [ ] Regenerate dataset report only if result schema docs require it; do not invent measured results.
- [ ] Run full test suite and `git diff --check`.

## Task 5: Final Verification

**Files:**
- All modified files.

**Interfaces:**
- Full local tests pass.
- No stack run is required for this infrastructure PR unless code changes require live validation; live flavor benchmarks are a follow-up PR.

- [ ] Run `uv run pytest -q`.
- [ ] Run `git diff --check`.
- [ ] Summarize remaining live-test work separately from implemented infrastructure.
