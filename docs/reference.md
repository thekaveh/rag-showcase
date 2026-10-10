# 7.20 Documentation Reference

Current task and operator guides come first. The historical specifications and
plans below preserve their dated implementation context; they are not current
setup instructions.

## 1. Current guides

| Document | Status | What it covers |
|---|---|---|
| [Overview](../docs/guide/overview.md) | Living | Concepts — how the seven approaches run under identical conditions, flavor aliases, and the fair-comparison guarantees |
| [Quick Start](../docs/guide/quickstart.md) | Living | One-command bring-up, prerequisites, and driving the multi-model comparison in Open WebUI |
| [Architecture diagrams](../docs/architecture.md) | Living | Detailed project architecture and seven-approach parallel flow diagrams |
| [System diagram (interactive)](../docs/diagrams/architecture.md) | Living | Rendered full-system architecture diagram (HTML/SVG in an inline iframe) |
| [Approach flow diagram (interactive)](../docs/diagrams/approach-flows.md) | Living | Rendered parallel-lane diagram of the seven approach flow phases (HTML/SVG in an inline iframe) |
| [Approach internals](../docs/approaches.md) | Living | Step-by-step flow, dependencies, tuning variables, tradeoffs, and measured performance for every approach |
| [Approach flavor tuning](../docs/approach-flavor-tuning.md) | Living | Open WebUI model aliases, benchmark flavor selection, and query-time versus index-time tuning knobs |
| [Experimental lazy graph RAG](../docs/lazy-graph-rag.md) | Living | Design and results of the seventh approach — a deterministic concept graph with budgeted query-time expansion |
| [Evaluation methodology](../docs/evaluation-methodology.md) | Living | Atlas/showcase ownership, evidence schema, resumable ladder, Ragas states, operational metrics, judge panel, and four-artifact contract |
| [Evaluation results and leaderboards](../docs/evaluation-results.md) | Generated | Complete static base and flavor rankings for every approach and metric |
| [Hardware sizing](../docs/hardware.md) | Living | Minimum and recommended hardware profiles for live stack, local models, and graph-heavy runs |
| [Running graph approaches locally](../docs/guide/local-graph-runs.md) | Living | Host-Ollama tuning, version parity, and the known graph-extraction blocker for a clean local graph run |
| [Atlas-reuse assessment](../docs/atlas-reuse-assessment.md) | Living | What reused cleanly, friction found, recommendations for Atlas |
| [Dependency contract ledger](../docs/dependency-contracts.md) | Living | Each consumed external dependency (LiteLLM, Weaviate, LightRAG, TEI, n8n, Atlas) and the exact pinned version its contract was verified against |
| [Corpus](../corpus/README.md) | Living | How to populate the corpus |
| [Dataset adapters](../corpus/adapters/README.md) | Living | The dataset fetch/adapter CLIs (GDELT, OpenAlex, STaRK, MITRE cyber) behind the candidate real-world graph rungs |
| [Dataset complexity report](../docs/dataset-complexity-report.md) | Living | Judge and canonical metric rankings by dataset complexity, with coverage and legacy fallback |
| [Live run result snapshots](../docs/results/README.md) | Living | Artifact ledger for committed evidence, summaries, matrices, and panel judgments |
| [n8n workflow](../n8n/README.md) | Living | Checked-in Adaptive-RAG workflow, Atlas seeding lifecycle, and workflow tuning knobs |
| [Live comparison](../docs/comparison.md) | Living | Side-by-side results of all seven approaches + live-validation findings (`think:false`, LightRAG role/query tuning, graph-native corpus behavior) |
| [Changelog](../CHANGELOG.md) | Living | Notable changes toward the first release (eval-check preflight, durable manifest config, infra pin-drift guard, seven-approach wording) |
| [Security policy](../SECURITY.md) | Governance | Vulnerability reporting channel and scope |

## 2. Historical specifications and plans

| Document | Status | What it records |
|---|---|---|
| [Design spec](../docs/superpowers/specs/2026-06-25-rag-showcase-design.md) | Historical | The approved design: six approaches, architecture, corpus, phasing (predates implementation — see its deviations note) |
| [Implementation plan](../docs/superpowers/plans/2026-06-25-rag-showcase.md) | Historical | The task-by-task implementation plan (Tasks 0–19, as-built) |
| [Approach flavors plan](../docs/superpowers/plans/2026-07-02-approach-flavors.md) | Historical | Follow-on plan that added the tunable flavor alias system |
| [Atlas LightRAG alignment plan](../docs/superpowers/plans/2026-07-02-atlas-lightrag-alignment.md) + [design](../docs/superpowers/specs/2026-07-02-atlas-lightrag-alignment-design.md) | Historical | Follow-on plan/design that wired LightRAG role models through Atlas inputs |
| [Cyber threat dataset plan](../docs/superpowers/plans/2026-07-03-cyber-threat-dataset.md) | Historical | Follow-on plan that added the bounded MITRE ATT&CK cyber-threat corpus rung |
| [Sortable leaderboards design](../docs/superpowers/specs/2026-07-17-sortable-evaluation-leaderboards-design.md) | Historical | Design for the sortable, filterable evaluation leaderboards |
| [Sortable leaderboards plan](../docs/superpowers/plans/2026-07-17-sortable-evaluation-leaderboards.md) | Historical | Implementation plan for the sortable leaderboards |
| [Consumer evaluation matrix plan](../docs/superpowers/plans/2026-07-13-consumer-evaluation-matrix.md) | Historical | Implementation plan for the consumer-owned, resumable RAG evaluation matrix and canonical-row store |
| [Approach lifecycle design](../docs/superpowers/specs/2026-07-16-approach-lifecycle-and-renewed-evaluation-design.md) | Historical | Design distinguishing deployed vs. researched approach families and scoping a fresh evaluation to only what rag-showcase deploys |
| [Atlas current-integration + comprehensive rerun plan](../docs/superpowers/plans/2026-07-16-atlas-current-lifecycle-and-comprehensive-rerun.md) | Historical | Plan to pin the latest Atlas `main`, finish local roadmap work, and produce a provenance-complete rerun of every approach and flavor |
| [Per-approach data-flow diagrams design](../docs/superpowers/specs/2026-07-17-per-approach-data-flow-diagrams-design.md) | Historical | Design for the seven per-approach, service-aware data-flow diagrams (implemented — see [Approach internals](../docs/approaches.md)) |
| [Per-approach data-flow diagrams plan](../docs/superpowers/plans/2026-07-17-per-approach-data-flow-diagrams.md) | Historical | Implementation plan for publishing the per-approach diagrams across all three documentation surfaces |
| [Three-surface opener remediation design](../docs/superpowers/specs/2026-07-31-three-surface-opener-remediation-design.md) | Historical | Design for a shared opener, project poster, native wiki output, and publication enforcement |
| [Three-surface opener remediation plan](../docs/superpowers/plans/2026-07-31-three-surface-opener-remediation.md) | Historical | Implementation and verification plan for the three-surface documentation corrections |
| [Atlas LightRAG role-model spec](../docs/atlas-lightrag-role-model-spec.md) | Implemented upstream | Historical Atlas-side spec for first-class LightRAG EXTRACT/KEYWORD/QUERY model wiring |
