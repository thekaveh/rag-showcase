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

### Fixed

- `eval-check` now resolves the Ollama endpoint from the active
  `LLM_PROVIDER_SOURCE` rather than a never-written `OLLAMA_ENDPOINT`.
- `start-all.sh` tolerates Atlas's exited-zero one-shot race only on the
  exact log signature, with a strict provider-aware readiness check.
