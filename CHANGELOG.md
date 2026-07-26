# Changelog

All notable changes to rag-showcase are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). There are no tagged
releases yet; this section tracks the unreleased work toward `0.1.0`.

## [Unreleased]

### Added

- `make eval-check`: a read-only preflight that verifies the evaluation's
  Atlas-infra dependencies — LiteLLM aliases, Weaviate plus its ingested
  collections, LightRAG (health and knowledge-graph population), the TEI
  reranker, n8n, and the required Ollama models — without running any
  ingestion, approach, or judge. It also warns on an Ollama client/server
  version skew and fails on an empty graph while graph aliases are declared.
- Durable `BASE_PORT: auto` and a named `profile: dev` environment bundle in
  the consumer manifest, so a manifest-driven start resolves a stable free
  port block and the correct compute sources on every host with no per-run
  flags.
- An `infra` pin-drift guard in `start-all.sh` that restores the pinned
  Atlas submodule SHA after a run (and a CI assertion that the gitlink is
  unchanged), until the upstream launcher respects the pin.
- A local-graph-run runbook (`docs/guide/local-graph-runs.md`) covering the
  host-Ollama tuning and the known graph-extraction blocker.
- A generated MkDocs documentation site and a GitHub wiki, both derived from
  the in-repo `docs/` source and kept in sync each change.
- `LICENSE` (Apache-2.0), `SECURITY.md`, and this changelog.

### Changed

- Adopted the Atlas durable-config wave: the `infra` submodule pin, the
  consumer manifest (`LLM_PROVIDER_SOURCE: auto` host-adaptive selection,
  sources committed under `env.values`), and the `start-all.sh` wrapper now
  pass no per-run source flags.
- n8n workflow activation no longer requires an `N8N_API_KEY` (upstream
  Atlas #720), so `start-all.sh` performs no manual publish or n8n restart.
- LiteLLM aliases declared in the manifest are compiled into `config.yaml`
  before the proxy boots, so they are discoverable at startup with no
  consumer-side reconcile or restart.
- Standardized the project description on "seven approaches" (six canonical
  plus the experimental `lazy-graph-rag`) across the manifest, plugin, CLI help,
  and documentation.
- `make lint` (ruff) and `make sortable-tables-test` are now part of the
  Makefile/CI validation gate, alongside `make test` and `make docs-check`.

### Fixed

- `eval-check` now resolves the Ollama endpoint from the active
  `LLM_PROVIDER_SOURCE` rather than a never-written `OLLAMA_ENDPOINT`.
- `start-all.sh` tolerates Atlas's exited-zero one-shot race only on the
  exact log signature, with a strict provider-aware readiness check.
- The TEI cross-encoder reranker discarded every already-scored batch when a
  later batch failed on requests spanning more than one rerank batch (as
  `hybrid-rag-high-recall` and `contextual-rag-high-recall` do by default);
  now only the failing batch degrades to unranked order, and prior batches'
  scores are preserved.
- The TEI reranker also silently dropped candidates from a structurally-valid
  but incomplete ranking response (fewer rows than texts sent, or an
  out-of-range `index`) — those hits vanished from the result entirely
  instead of falling back to unranked order like every other malformed-
  response shape. Now tracked and kept.
- A repeated (duplicate) `index` in a TEI reranker response was read as "two
  candidates ranked": it duplicated the referenced hit in the output and, via
  the fix above's own missing-index accounting, crowded a genuinely distinct
  unranked candidate out of `top_n` — even when `top_n` was large enough to
  fit every original hit. Repeated indices are now ignored after the first.
- `lightrag.query()` no longer raises on a non-dict `/query` response body
  from LightRAG; degrades to an empty/error response instead of crashing
  the request.
- `contextualize()` no longer raises when an ingestion chunk's LLM
  completion content is non-string; guards before calling `.strip()`.
- Answer/blurb response paths no longer raise `AttributeError` on a `None`
  message from a malformed LLM completion.
- LiteLLM and n8n-adapter response parsing now guard malformed/non-JSON
  response bodies instead of raising or silently miscoercing metrics.
- Evaluation runs no longer abort the entire matrix on a single `None`
  completion from the approach under test (a gateway 200 with a null body).
- Reranker/evaluator scores of `True`/`False` (a Python `bool`, an `int`
  subclass) are no longer coerced to `1.0`/`0.0`; they are treated as an
  absent score, matching the intended numeric-score contract.
- `run-dataset-ladder.py`'s outer subprocess timeout now covers
  `atlas_job.py`'s full sequential ingest-then-poll budget, and the poll
  loop's own HTTP timeout is capped to the remaining deadline, eliminating
  a class of ingest-timeout overshoot.
- `lazy_graph`'s cold-cache index build is now guarded by a per-cache-key
  lock, preventing duplicate concurrent builds of the same graph.
- `evaluation_summary.py` no longer silently drops a metric with no
  recognized degrade shape from the evaluated/not_evaluable/error/timeout
  reconciliation.
- The four corpus adapter CLIs (`stark_export.py`, `gdelt_events.py`,
  `openalex_scholarly.py`, `cyber_threat_intel.py`) now reject a
  non-positive `--limit` instead of silently exporting the wrong slice.
- `eval_preflight.envval()` now checks `is_file()` instead of `exists()`, so
  a directory auto-created at a bind-mount target before `infra/.env`
  materializes degrades to a missing value instead of crashing with
  `IsADirectoryError`.
- LightRAG's query-profile cache was gated on dict truthiness
  (`if _PROFILE_CACHE:`), so a valid-but-empty profiles file made the cache
  permanently falsy and every graph-rag request (the only caller that passes
  `profile=` to `lightrag.query()`) re-read and re-parsed the profiles file
  synchronously instead of caching it once.
- `compare/leaderboards.py` hardcoded `base_family == "lazy-graph-rag"` to
  flag an approach experimental instead of checking the shared
  `EXPERIMENTAL_APPROACHES` set that `run_matrix.py` already used; a second
  experimental approach would have been silently mislabeled canonical in
  the published leaderboard.
- `verify_atlas_runtime.py`'s startup convergence poll no longer crashes on a
  transient `docker ps` daemon error; it now retries on the next poll,
  matching the tolerance its sibling `docker inspect` call already had.
- `eval_preflight.py`'s docker probes (`run_live_probes`, `_backend_running`)
  no longer crash the whole `make eval-check` preflight when the `docker`
  CLI is missing from `PATH`; they degrade to "docker unavailable" like the
  already-handled timeout case.
- `compare/flavors.py` and `backend_plugins/rag/common/flavors.py` now
  reject a bare `true`/`false` for a numeric flavor param (`retrieve_k`,
  `alpha`, etc.) instead of silently coercing it via `bool`'s `int`
  subclass behavior (`retrieve_k: true` → `1`), raising the load-time
  `ValueError` the loader's docstring promises.
- `scripts/docs/render_diagrams.py`'s fallback PNG renderer wrote directly
  into the shared final PNG path with only a check-then-act `png.exists()`
  guard; two concurrent local `build()` invocations could interleave or
  truncate each other's output into the same file. It now renders to a
  unique temp file and atomically publishes it via `os.replace`.
