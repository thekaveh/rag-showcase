# Cyber Threat Dataset Implementation Plan

**Status:** Historical artifact — implemented, as-built (the dataset is
committed and measured). Not a live task list.
**Section numbering:** primary sections use the domain-specific `Task N` scheme this plan was executed under; kept as-built rather than renumbered.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bounded, committed cyber-threat-intel dataset rung before running the expanded RAG flavor comparison.

**Architecture:** Generate a real-world graph-native markdown corpus from public MITRE ATT&CK Enterprise STIX data, keeping the slice small enough for local LightRAG indexing. Align queries to the actual corpus contents: intrusion groups, malware/tools, techniques, mitigations, campaigns, and relationship paths. Mark the dataset as measured only after live matrix/judge snapshots exist; until then it is a committed candidate with generated source files.

**Tech Stack:** Python, pytest, YAML manifests, MITRE ATT&CK STIX JSON, markdown corpus files, existing dataset ladder harness.

## Global Constraints

- Do not assume hardware beyond the repo's documented Atlas-supported profiles.
- Keep the dataset bounded; avoid a full ATT&CK export for the first flavor sweep.
- The committed query file must ask answerable questions over the committed corpus.
- Do not mark the dataset `measured` until matrix and judge snapshots are produced.
- Preserve existing measured baseline and graph-native result snapshots.

---

## Task 1: Pin Corpus Shape With Tests

**Files:**
- Modify: `tests/test_dataset_ladder.py`
- Modify: `tests/test_dataset_adapter_clis.py`

**Interfaces:**
- `cyber_threat_intel` remains in `compare/datasets.yaml`.
- Its query file contains graph-heavy questions answerable from MITRE ATT&CK content.
- Its committed corpus directory contains markdown files with `Relations:` sections.

- [ ] Add tests that the cyber dataset corpus path exists and has at least 20 markdown dossiers.
- [ ] Add tests that cyber queries mention ATT&CK concepts present in the corpus, not unavailable NVD-only concepts.
- [ ] Run focused tests and verify failure before creating the corpus.

## Task 2: Improve The Adapter For Named Relation Output

**Files:**
- Modify: `corpus/adapters/cyber_threat_intel.py`
- Test: `tests/test_dataset_adapter_clis.py`

**Interfaces:**
- Existing CLI remains: `python corpus/adapters/cyber_threat_intel.py --output <dir> --limit <n>`.
- Output markdown resolves relationship target/source names instead of only opaque STIX IDs.
- Output is deterministic for a given ATT&CK bundle and limit.

- [ ] Add a unit/CLI test that generated relation lines contain human-readable names.
- [ ] Run focused test and verify failure.
- [ ] Update adapter to build an object-id to name map.
- [ ] Run focused test and verify pass.

## Task 3: Generate And Commit The Bounded Corpus

**Files:**
- Create: `corpus/cyber_threat_intel/*.md`
- Modify: `compare/datasets.yaml`
- Modify: `demo/cyber_threat_intel_queries.yaml`

**Interfaces:**
- `compare/datasets.yaml` points `cyber_threat_intel.corpus_path` to `corpus/cyber_threat_intel`.
- Dataset remains `status: candidate` until live snapshots exist.
- Query file asks about groups, software, techniques, campaigns, mitigations, and relationship chains.

- [ ] Generate a bounded corpus with the improved adapter.
- [ ] Replace unanswerable CVE/product questions with ATT&CK-answerable graph questions.
- [ ] Run dataset tests and verify pass.

## Task 4: Docs And Verification

**Files:**
- Modify: `docs/dataset-complexity-report.md`
- Modify: `corpus/README.md`

**Interfaces:**
- Docs state cyber is a committed candidate corpus ready for live measurement.
- Report still marks scores as pending until the live run is produced.

- [ ] Regenerate dataset complexity report.
- [ ] Update corpus docs to mention the committed cyber slice.
- [ ] Run `uv run pytest -q` and `git diff --check`.
