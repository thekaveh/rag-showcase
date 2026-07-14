# Consumer-Owned RAG Evaluation Matrix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the ad hoc result contract with a consumer-owned, Atlas-backed evaluation matrix that resumes safely, evaluates eligible evidence through Atlas, and produces deterministic coverage-aware reports without breaking historical outputs.

**Architecture:** `rag-showcase` remains the experiment orchestrator. A versioned manifest selects datasets, aliases, Ragas metrics, judge models, retries, timeouts, and concurrency; a local runner calls aliases through Atlas LiteLLM, normalizes plugin evidence, calls Atlas `POST /api/rag/evaluate`, and appends one durable row per completed cell. Existing matrix and judgment JSON remain compatibility views while deterministic summary JSON and Markdown reporting derive from canonical rows.

**Tech Stack:** Python 3.10+, Pydantic 2, PyYAML, HTTPX, pytest, Ruff, Atlas OpenAI-compatible and RAG-evaluation HTTP APIs, MkDocs three-surface documentation.

## Global Constraints

- Atlas remains provider-neutral infrastructure; no Atlas internals are imported or modified.
- The default matrix remains the six canonical approaches; experimental aliases require explicit selection.
- No operating-system, accelerator, model-provider, or hardware assumption is embedded in runner behavior.
- Ragas evaluator metrics, deterministic operational metrics, and subjective judge scores remain separate.
- Missing evidence produces explicit `not_evaluable` metric state; it never fabricates context or erases the answer.
- Existing committed matrix/judgment snapshots remain readable and the current dataset report keeps working during migration.
- Canonical documentation sources are edited, generated surfaces are produced by `make docs-check`, and generated outputs are not hand-authored.

---

### Task 1: Versioned Matrix Manifest and Evidence Contract

**Files:**
- Create: `compare/evaluation.yaml`
- Create: `compare/evaluation.py`
- Modify: `backend_plugins/rag/common/openai_io.py`
- Test: `tests/test_evaluation_manifest.py`
- Test: `backend_plugins/rag/tests/test_openai_io.py`

**Interfaces:**
- Produces: `load_manifest(path: Path) -> EvaluationManifest`, `load_dataset(manifest, dataset_id) -> DatasetSpec`, `evidence_for_base(manifest, base) -> str`, and `completion_evidence(payload: dict) -> dict`.
- Produces: an optional OpenAI-compatible top-level `rag_showcase` extension containing schema version, ordered source snippets, and server metrics; rendered-content parsing remains the transport fallback.

- [x] **Step 1: Write manifest validation tests** for schema version `1`, unique datasets/approaches, known Ragas metrics, positive timeout/concurrency bounds, and required judge models when enabled.
- [x] **Step 2: Run `uv run pytest tests/test_evaluation_manifest.py -q`** and verify failures are caused by the absent module and manifest.
- [x] **Step 3: Implement Pydantic manifest models and path resolution** with `compare/datasets.yaml` as the referenced dataset catalog and canonical aliases from `compare/flavors.py`.
- [x] **Step 4: Write backend response-contract tests** asserting structured source snippets/metrics are additive and JSON/SSE OpenAI compatibility remains intact.
- [x] **Step 5: Run the backend tests and verify RED**, then add the `rag_showcase` extension at the shared `build_response` choke point.
- [x] **Step 6: Add structured-first, rendered-content-fallback evidence parsing** and verify nested n8n details, multiline snippets, usage, response id, and missing-evidence behavior.
- [x] **Step 7: Run `uv run pytest tests/test_evaluation_manifest.py backend_plugins/rag/tests/test_openai_io.py tests/test_compare_harness.py -q`** and verify GREEN.

### Task 2: Append-Safe Runner and Atlas Evaluator Client

**Files:**
- Modify: `compare/evaluation.py`
- Modify: `compare/run_matrix.py`
- Create: `tests/test_evaluation_runner.py`
- Modify: `tests/test_run_matrix.py`
- Modify: `tests/test_compare_harness.py`

**Interfaces:**
- Produces: `JsonlStore(path).completed_ids()` and `.append(row)` with duplicate protection and flush/fsync durability.
- Produces: `AtlasEvaluationClient.evaluate(question, answer, contexts, reference, metrics) -> dict`.
- Produces: `run_evaluation(run_spec, invoke, evaluator, store) -> list[dict]`, where callables are injectable for deterministic tests.
- `compare/run_matrix.py` remains the host CLI and compatibility JSON writer.

- [x] **Step 1: Write failing 2x2 runner tests** asserting four stable row ids, one row per cell, explicit error/timeout rows, and successful cells surviving another cell's failure.
- [x] **Step 2: Write failing resume tests** asserting a pre-existing completed row is not invoked again and duplicate row identities are rejected rather than silently appended.
- [x] **Step 3: Implement stable row identity, JSONL loading/appending, retries, timeout classification, and sequential/concurrent task execution** with default concurrency `1`.
- [x] **Step 4: Write failing evaluator tests** for eligible metrics, missing contexts, missing references, evaluator failure, model metadata, and metric-class separation.
- [x] **Step 5: Implement the HTTP client** against configurable Atlas `POST /api/rag/evaluate`, splitting reference-required metrics and preserving `ok`, `partial`, `not_evaluable`, `error`, and `disabled` states.
- [x] **Step 6: Refactor `run_matrix.py`** to validate before calls, append canonical rows immediately, skip completed ids on resume, and still emit the current matrix JSON view.
- [x] **Step 7: Add CLI/env inputs** for manifest, dataset id, run id, canonical JSONL, summary path, evaluator URL, aliases/flavors, and compatibility output while retaining safe `--help` behavior.
- [x] **Step 8: Run `uv run pytest tests/test_evaluation_runner.py tests/test_run_matrix.py tests/test_compare_harness.py -q`** and verify GREEN.

### Task 3: Deterministic Summaries and Optional Judge Join

**Files:**
- Create: `compare/evaluation_summary.py`
- Create: `compare/summarize.py`
- Modify: `compare/judge.py`
- Create: `tests/test_evaluation_summary.py`
- Modify: `tests/test_judge.py`

**Interfaces:**
- Produces: `build_summary(rows: list[dict], judgments: dict | None) -> dict` with dataset and overall sections.
- Produces: `write_summary(rows_path, output_path, judgments_path=None)` with byte-stable sorted JSON.
- Judge models default from `compare/evaluation.yaml`; `JUDGE_MODELS` remains an explicit operator override.

- [x] **Step 1: Write failing summary tests** for per-dataset and overall Ragas means, latency/error coverage, failed and unevaluable denominators, explicit ties, and longitudinal per-approach progression.
- [x] **Step 2: Implement pure deterministic aggregation and tie grouping** without timestamps or row-order dependence in the summary function.
- [x] **Step 3: Write failing judge-join tests** proving judge scores live in a separate metric section and judge failure does not change Ragas or operational aggregates.
- [x] **Step 4: Implement optional judgment joining and the summary CLI**; malformed or absent judge artifacts produce explicit disabled/error metadata rather than deleting other metrics.
- [x] **Step 5: Make judge model selection manifest-driven** while preserving stable anonymization, batching, `think:false`, and existing output compatibility.
- [x] **Step 6: Run `uv run pytest tests/test_evaluation_summary.py tests/test_judge.py -q`** and verify GREEN.

### Task 4: Dataset-Ladder and Historical Compatibility

**Files:**
- Modify: `scripts/run-dataset-ladder.py`
- Modify: `compare/datasets.yaml`
- Modify: `compare/report_datasets.py`
- Modify: `tests/test_dataset_ladder_runner.py`
- Modify: `tests/test_dataset_report.py`

**Interfaces:**
- Dataset runs produce four documented artifacts: compatibility matrix JSON, compatibility judgment JSON, canonical evidence JSONL, and deterministic evaluation summary JSON.
- Measured dataset rows gain optional `evidence_snapshot` and `evaluation_snapshot`; old rows with only matrix/judgment snapshots remain valid.

- [x] **Step 1: Write failing ladder tests** asserting deterministic run/dataset ids, canonical filenames, resume propagation, summary generation after judges, and atomic snapshot publication only after validation.
- [x] **Step 2: Integrate canonical paths into the ladder** and copy validated artifacts into `docs/results` alongside existing snapshots.
- [x] **Step 3: Write failing report tests** for separate judge, Ragas, operational, coverage, failure, and unevaluable columns with legacy fallback.
- [x] **Step 4: Update report generation** to prefer canonical summary data and retain the current judge-only behavior for historical datasets lacking new summaries.
- [x] **Step 5: Run `uv run pytest tests/test_dataset_ladder_runner.py tests/test_dataset_report.py -q`** and verify GREEN.

### Task 5: Canonical Documentation and Migration Guidance

**Files:**
- Modify: `README.md`
- Modify: `docs/evaluation-methodology.md`
- Modify: `docs/comparison.md`
- Modify: `docs/results/README.md`
- Modify: `docs/approaches.md`
- Modify: `docs/manifest.yaml` only if a new canonical page is required after reviewing the existing hierarchy.

**Interfaces:**
- Documents the Atlas/showcase ownership boundary, exact invocation flow, manifest schema, evidence capability, result taxonomy, resume semantics, output layout, historical compatibility, and limitations.

- [x] **Step 1: Update methodology** with numbered sections for consumer ownership, request/evidence flow, Atlas evaluation, judge separation, deterministic summaries, and coverage-aware ranking.
- [x] **Step 2: Update result documentation** with canonical/compatibility artifact naming and explain why graph answers without retrievable contexts can be answered but remain unevaluable for faithfulness.
- [x] **Step 3: Update README/comparison links and summaries** without claiming unrun live scores.
- [x] **Step 4: Run `make docs-check`** and fix broken links, manifest drift, or generated-surface differences.

### Task 6: Full and Live Verification

**Files:**
- Modify only files implicated by failures found during verification.
- Produce live artifacts under `compare/results/`; publish to `docs/results/` only after complete validation.

**Interfaces:**
- A controlled two-alias live smoke proves Atlas alias invocation, Ragas evaluation, interrupted resume, and validated output before a full ladder run is attempted.

- [ ] **Step 1: Run `uv run pytest tests backend_plugins/rag/tests -q`**, `uv run ruff check backend_plugins compare scripts tests`, and `make docs-check`.
- [ ] **Step 2: Run Atlas consumer-manifest/preflight and Compose configuration checks** using the pinned submodule and showcase overlay.
- [ ] **Step 3: Start the scoped RAG stack without hardware assumptions**; if startup fails, diagnose and fix showcase-owned faults while recording genuine external blockers.
- [ ] **Step 4: Run a live two-approach/two-dataset smoke**, interrupt after at least one canonical row, resume, and verify no duplicate row ids.
- [ ] **Step 5: Run the six canonical approaches across eligible measured ladder datasets**, evaluate eligible rows, run the optional judges, validate all artifacts, regenerate reports, and tear the stack down.
- [ ] **Step 6: Re-run all static verification after generated report changes**, inspect the final diff, commit focused changes, push, open a PR into `develop`, and update issue #24 with evidence.
