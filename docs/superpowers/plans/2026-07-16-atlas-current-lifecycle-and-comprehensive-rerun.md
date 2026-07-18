# Atlas Current Integration and Comprehensive Rerun Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Pin rag-showcase to the latest Atlas `main`, finish all applicable local roadmap work, publish the nine-family lifecycle comparison, and produce a fresh, provenance-complete evaluation of every deployed base approach and declared flavor.

**Architecture:** Atlas remains the generic infrastructure owner and rag-showcase remains the consumer. Atlas owns service lifecycle, model/provider routing, ingestion jobs, LightRAG query-profile validation, and Ragas evaluation; rag-showcase owns approach endpoints, profile selection, n8n response normalization, datasets, judges, result aggregation, and documentation. Candidate Graphify RAG and LLM Wiki RAG are documented but not implemented or scored.

**Tech Stack:** Atlas consumer manifest, Docker Compose, FastAPI, LiteLLM, Ollama localhost, LightRAG, Neo4j, Weaviate, TEI, n8n, Ragas, pytest, Ruff, MkDocs Material, GitHub CLI.

## Global Constraints

- Work from `codex/approach-lifecycle-rerun-design`, based on current `develop`; never commit directly to `main`.
- Pin `infra` to the exact latest commit fetched from Atlas `origin/main` immediately before validation and again immediately before launch.
- Launch Atlas with project name `rag-showcase` and a dynamically selected free 110-port block.
- Use Atlas `ollama-localhost`; do not launch container Ollama.
- ComfyUI is not a member of Atlas's `gen-ai-rag` track and is not consumed by this showcase; do not pass a ComfyUI source or stop/alter an existing host ComfyUI process.
- Keep provider and hardware requirements out of defaults and canonical claims. Record the actual runtime used by the live experiment as provenance.
- Do not assign scores to Graphify RAG or LLM Wiki RAG.
- Use fresh dataset-scoped ingestion and cold resets between measured datasets.
- Preserve base-family and flavor rankings as separate evaluation tiers.
- Update canonical docs, then regenerate and verify site/wiki surfaces with `make docs-check`.

---

### Task 1: Adopt Current Atlas Main and Revalidate Roadmap Issues

**Files:**
- Modify: `infra` gitlink
- Modify: `docs/superpowers/specs/2026-07-16-approach-lifecycle-and-renewed-evaluation-design.md`

**Interfaces:**
- Consumes: Atlas `origin/main`, GitHub issues rag-showcase #22, #23, and #27.
- Produces: exact Atlas pin and an updated 12-flavor/380-cell design contract.

- [ ] **Step 1: Fetch and record Atlas main**

Run:

```bash
git -C infra fetch origin main --prune
git -C infra log -1 --format='%H %ad %s' --date=iso-strict origin/main
```

Expected: one exact `origin/main` commit; no use of Atlas `develop` or an open PR head.

- [ ] **Step 2: Move the submodule gitlink to the fetched commit**

Run:

```bash
git -C infra checkout --detach origin/main
git add infra
```

Expected: `git submodule status infra` reports the fetched SHA without a leading `-`.

- [ ] **Step 3: Update the approved design counts**

Change the design from eleven to twelve declared flavor aliases because Atlas #415 unblocks a new `graph-rag-rerank` flavor. Change 220 flavor cells to 240 and 360 total cells to 380.

- [ ] **Step 4: Validate issue dependencies from primary sources**

Run:

```bash
gh issue view -R thekaveh/atlas 414 --json state,closedAt,url
gh issue view -R thekaveh/atlas 415 --json state,closedAt,url
gh issue view -R thekaveh/atlas 533 --json state,closedAt,url
gh issue view -R thekaveh/atlas 379 --json state,closedAt,url
```

Expected: all four are closed as completed on Atlas main.

### Task 2: Move Graph Flavors to Atlas Query Profiles and Add Reranking

**Files:**
- Modify: `atlas.consumer.yml`
- Modify: `config/atlas.env.user`
- Modify: `backend_plugins/rag/flavors.yaml`
- Modify: `compare/flavors.yaml`
- Modify: `backend_plugins/rag/common/lightrag.py`
- Modify: `backend_plugins/rag/approaches/graph.py`
- Modify: `tests/test_litellm_model_manifest.py`
- Modify: `tests/test_compare_flavors.py`
- Modify: `backend_plugins/rag/tests/test_graph.py`
- Create: `backend_plugins/rag/tests/test_lightrag_profiles.py`

**Interfaces:**
- Consumes: Atlas-generated `LIGHTRAG_QUERY_PROFILES_FILE`, profile precedence `request > profile > service env default`.
- Produces: `lightrag.query(question, profile=..., options=...)` and a rerank-enabled `graph-rag-rerank` alias.

- [ ] **Step 1: Write failing manifest/profile tests**

Assert that `atlas.consumer.yml` declares `graph-rag`, `graph-rag-fast`, `graph-rag-wide`, and `graph-rag-rerank` under `lightrag_query_profiles`; that the rerank profile enables reranking; and that graph rows in local flavor YAML contain descriptions but no duplicated `mode`, `top_k`, `chunk_top_k`, `max_total_tokens`, or `enable_rerank` values.

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
uv run pytest tests/test_litellm_model_manifest.py tests/test_compare_flavors.py backend_plugins/rag/tests/test_graph.py backend_plugins/rag/tests/test_lightrag_profiles.py -q
```

Expected: failures for missing Atlas profiles, missing rerank alias, and missing profile resolution.

- [ ] **Step 3: Declare Atlas-owned profiles**

Add `lightrag_query_profiles.version: 1` to `atlas.consumer.yml` with:

```yaml
- name: graph-rag
  mode: hybrid
  top_k: 10
  chunk_top_k: 5
  max_total_tokens: 12000
  enable_rerank: false
- name: graph-rag-fast
  mode: local
  top_k: 5
  chunk_top_k: 3
  max_total_tokens: 8000
  enable_rerank: false
- name: graph-rag-wide
  mode: hybrid
  top_k: 30
  chunk_top_k: 12
  max_total_tokens: 24000
  enable_rerank: false
- name: graph-rag-rerank
  mode: hybrid
  top_k: 10
  chunk_top_k: 5
  max_total_tokens: 12000
  enable_rerank: true
```

Set `LIGHTRAG_RERANK_ADAPTER_ENABLED=true` in `config/atlas.env.user`.

- [ ] **Step 4: Implement profile loading and precedence**

Load the Atlas JSON registry from `LIGHTRAG_QUERY_PROFILES_FILE`, require schema version 1, reject duplicate/missing profile names, and merge profile fields into the LightRAG `/query` payload before explicit request options. Keep the existing environment defaults as the final fallback.

- [ ] **Step 5: Remove duplicated graph knobs and add the new alias**

Keep local graph flavor rows only for alias, base, label, description, and `requires_reingest`. Add `graph-rag-rerank` to both local manifests and the explicit consumer LiteLLM alias list. `graph.py` selects the Atlas profile using the resolved request alias.

- [ ] **Step 6: Run focused tests and verify GREEN**

Run the Task 2 pytest command and expect all tests to pass.

### Task 3: Preserve n8n Downstream Evidence

**Files:**
- Modify: `n8n/adaptive-rag.workflow.json`
- Modify: `backend_plugins/rag/approaches/n8n.py`
- Modify: `backend_plugins/rag/tests/test_n8n.py`
- Modify: `tests/test_n8n_workflow_contract.py`
- Modify: `tests/test_evaluation_manifest.py`

**Interfaces:**
- Consumes: delegated completion `rag_showcase.sources`, `rag_showcase.metrics`, and route metadata.
- Produces: adaptive completion with real downstream contexts and additive `adaptive` metadata.

- [ ] **Step 1: Write failing evidence-propagation tests**

Mock a workflow response containing downstream sources and metrics. Assert that the wrapper preserves those sources, adds one classifier LLM call, reports outer latency, and stores route/approach under `rag_showcase.adaptive` rather than injecting a route marker as grounding context.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest backend_plugins/rag/tests/test_n8n.py tests/test_n8n_workflow_contract.py tests/test_evaluation_manifest.py -q
```

Expected: evidence assertions fail against the current route-marker-only response.

- [ ] **Step 3: Preserve structured evidence in the workflow**

Update the Shape node to return `answer`, `route`, `approach`, and the delegated `rag_showcase` object.

- [ ] **Step 4: Normalize evidence in the plugin**

Parse only well-typed downstream sources and metrics. Return no fake source when evidence is absent. Add `adaptive: {route, approach}` metadata and count the classifier call in the outer metrics.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 3 pytest command and expect all tests to pass.

### Task 4: Publish the Dedicated Lifecycle Comparison

**Files:**
- Modify: `docs/approaches.md`
- Modify: `docs/evaluation-methodology.md`
- Modify: `docs/approach-flavor-tuning.md`
- Modify: `docs/components/n8n.md`

**Interfaces:**
- Consumes: deployed code, Atlas contracts, Graphify primary documentation, and Karpathy's LLM Wiki proposal.
- Produces: a metrics-free nine-family comparison before measured results.

- [ ] **Step 1: Add the knowledge-lifecycle table**

Place it after the shared evaluation contract and before measured results. Include status and a separate `Employed in showcase?` column using `Yes`, `Experimental`, or `No - candidate` (adoption undecided).

- [ ] **Step 2: Add the query/evidence companion table**

Compare tool/routing selection, retrieval, reranking, generation ownership, model work, evidence, tuning, best fit, and failure modes. Mark Graphify RAG and LLM Wiki RAG as unimplemented and unmeasured.

- [ ] **Step 3: Update related canonical documentation**

Explain Atlas query-profile ownership, the rerank adapter, n8n evidence propagation, agent trajectory ephemerality, LightRAG ingest-time graph construction, lazy graph first-query construction, and candidate boundaries.

- [ ] **Step 4: Run documentation checks**

Run:

```bash
make docs-check
```

Expected: generated site/wiki are deterministic and MkDocs strict build passes.

### Task 5: Add Reproducible Two-Tier Evaluation Orchestration

**Files:**
- Modify: `scripts/run-dataset-ladder.py`
- Modify: `compare/flavors.py`
- Modify: `compare/report_datasets.py`
- Modify: `compare/datasets.yaml`
- Modify: `tests/test_dataset_ladder_runner.py`
- Modify: `tests/test_dataset_report.py`

**Interfaces:**
- Consumes: one fresh ingestion per dataset.
- Produces: canonical base artifacts plus separate `*-flavors-*` artifacts from the same ingestion.

- [ ] **Step 1: Write failing two-tier tests**

Assert that `--include-flavor-tier` exists, selects every non-base alias exactly once, writes flavor-specific artifact names, preserves base snapshot fields, adds flavor snapshot fields, and never cold-resets or re-ingests between tiers of one dataset.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_dataset_ladder_runner.py tests/test_dataset_report.py -q
```

Expected: failures for the absent option and artifact tier.

- [ ] **Step 3: Implement tiered execution**

Add a helper that returns every declared flavor alias excluding the seven base names. Run the existing base matrix first, then the flavor matrix against the same ingestion. Give flavor artifacts `live-<date>-<dataset>-flavors-{matrix,judgments,evidence,evaluation}` names.

- [ ] **Step 4: Persist and report flavor snapshots**

Add flavor snapshot paths to measured dataset rows and render a separate per-dataset flavor section without mixing its ranking into the base leaderboard.

- [ ] **Step 5: Run focused tests and verify GREEN**

Run the Task 5 pytest command and expect all tests to pass.

### Task 6: Make Launch Identity, Sources, and Port Allocation Explicit

**Files:**
- Create: `scripts/select-atlas-base-port.py`
- Modify: `scripts/start-all.sh`
- Modify: `tests/test_dataset_ladder_runner.py`
- Create: `tests/test_select_atlas_base_port.py`

**Interfaces:**
- Consumes: Atlas topology's reserved offsets and current host socket state.
- Produces: a free `BASE_PORT..BASE_PORT+109` block and an explicit Atlas launch command.

- [ ] **Step 1: Write failing port-selection and startup-contract tests**

Assert that occupied candidate ports reject the whole block, the selector returns the first wholly free 110-port block, and `start-all.sh` passes `--project rag-showcase`, `--base-port`, `--llm-provider-source ollama-localhost`, and `--comfyui-source disabled`.

- [ ] **Step 2: Run tests and verify RED**

Run:

```bash
uv run pytest tests/test_select_atlas_base_port.py tests/test_dataset_ladder_runner.py -q
```

- [ ] **Step 3: Implement the selector and launch wiring**

Probe every TCP port in each candidate 110-port block. Accept `RAG_SHOWCASE_BASE_PORT` only when its entire block is free; otherwise select from safe candidate blocks. Pass the selected value directly into Atlas startup immediately after the probe.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the Task 6 pytest command and expect all tests to pass.

### Task 7: Static Verification and Issue Disposition

**Files:**
- No planned file changes. A failure returns to the task that owns the affected
  contract; verification is not a catch-all refactoring step.

- [ ] **Step 1: Run full static verification**

Run:

```bash
git diff --check
uv run ruff check compare ingest scripts backend_plugins/rag tests
uv run pytest tests backend_plugins/rag/tests -q
make docs-check
```

Expected: all commands pass.

- [ ] **Step 2: Run current Atlas consumer validation**

Run:

```bash
cp -n infra/.env.example infra/.env
(cd infra && ./start.sh --consumer ../atlas.consumer.yml env backfill)
(cd infra && ./start.sh --consumer ../atlas.consumer.yml compose validate)
(cd infra && ./start.sh --consumer ../atlas.consumer.yml doctor)
```

Expected: valid manifest, profiles, plugin, workflow, Compose, and model declarations.

- [ ] **Step 3: Disposition local issues**

After tests and live evidence, comment and close #22 and #23 as completed. Comment on #27 with Atlas #379 evidence and close it as not planned/superseded because runtime lifecycle is now Atlas-owned and the showcase remains provider-neutral; document the actual runtime in each experiment instead of maintaining a runtime-specific local feature.

### Task 8: Launch and Smoke the Live Stack

**Files:**
- Runtime only: `infra/.env`, generated Atlas consumer artifacts, Docker state.

- [ ] **Step 1: Re-fetch Atlas main immediately before launch**

If `origin/main` advanced, update the gitlink, rerun Task 7, and only then continue.

- [ ] **Step 2: Verify host services and choose ports**

Confirm `http://127.0.0.1:11434/api/version` responds and required models exist. Record the existing ComfyUI localhost process but leave it untouched because ComfyUI is disabled for this track. Run the port selector and retain its full-block audit output.

- [ ] **Step 3: Launch rag-showcase Atlas**

Run service-only startup with `PROJECT_NAME=rag-showcase`, the selected base port, `ollama-localhost`, `comfyui disabled`, LightRAG container, TEI container CPU, and the consumer manifest.

- [ ] **Step 4: Verify runtime contracts**

Check Docker names, `/v1/models`, all seven base aliases, all twelve flavor aliases, LightRAG health/profile registry, rerank adapter health, n8n webhook, Weaviate, Neo4j, and evaluator answer-relevancy/faithfulness smoke requests.

### Task 9: Run the Fresh Comprehensive Dataset Ladder

**Files:**
- Create/replace dated files under `compare/results/`
- Create/replace dated files under `docs/results/`
- Modify: `compare/datasets.yaml`
- Regenerate: `docs/dataset-complexity-report.md`

- [ ] **Step 1: Run all measured datasets with the flavor tier**

Run:

```bash
uv run python scripts/run-dataset-ladder.py --include-flavor-tier --date-stamp 2026-07-16
```

Expected per dataset: cold reset, fresh Atlas ingestion, completed LightRAG drain, contextual index, 140 total base cells across the ladder, 240 total flavor cells, Ragas evaluation, two-judge results, and copied canonical artifacts.

- [ ] **Step 2: Validate artifact coverage**

Require exactly 380 successful-or-explicit-error rows, no duplicate row ids, evaluator status for every successful row, complete judge verdicts, ingestion provenance, and profile/configuration hashes. A transport failure is not a score.

- [ ] **Step 3: Tear the stack down**

Run `scripts/stop-all.sh` after preserving logs and artifacts. Verify no `rag-showcase-*` containers remain; do not stop unrelated Atlas projects, Ollama, or host ComfyUI.

### Task 10: Refresh Results Documentation and Complete GitFlow

**Files:**
- Modify: `docs/comparison.md`
- Modify: `docs/evaluation-methodology.md`
- Modify: `docs/approaches.md`
- Modify: `docs/approach-flavor-tuning.md`
- Modify: `docs/results/README.md`
- Modify: `README.md`
- Regenerate three documentation surfaces.

- [ ] **Step 1: Update empirical reporting from artifacts**

Publish base and flavor rankings separately, dataset-ladder progression, latency distributions, success/error rates, Ragas coverage and scores, judge means/disagreement, model/runtime provenance, graph profile revisions, and rerank-on versus rerank-off effects.

- [ ] **Step 2: Verify all documentation and code**

Repeat Task 7 static verification and run a final result-artifact consistency audit.

- [ ] **Step 3: Commit and push the feature branch**

Commit scoped changes and generated result artifacts, push, open a PR to `develop`, wait for required checks, and merge.

- [ ] **Step 4: Promote develop to main**

Open a subsequent `develop` to `main` PR, wait for checks, merge, and synchronize `develop` from `main` if repository policy requires it.

- [ ] **Step 5: Clean repository state**

Delete merged feature branches locally and remotely, close or merge every rag-showcase PR, prune remotes, remove stale worktrees, and verify only `main` and `develop` remain locally and remotely apart from GitHub-managed branches.
