# 5.4 Dataset Complexity Report

This generated report is the dataset-ladder and per-query view, not the
canonical all-metric ranking presentation. The complete static base and
flavor tables for every approach and metric are in
[`evaluation-results.md`](evaluation-results.md).

It tracks approach rankings by input dataset, ordered from the
simplest curated corpus to increasingly graph-heavy real-world candidates.
It deliberately reports by dataset rather than by vector/graph collection,
because the comparison question is how each RAG approach behaves as the
input problem becomes more relational, temporal, and multi-hop.
Each row also names the Atlas ingestion profile whose revision and job id
are stored with newly generated matrix and judgment snapshots.

For the run protocol, model roles, approach invocation details, and
judge-panel design, see [`evaluation-methodology.md`](evaluation-methodology.md).
Committed evidence and provenance are listed in
[`results/README.md`](results/README.md).
For approach-by-approach internals and tuning surfaces, see
[`approaches.md`](approaches.md).

## 1. Dataset Complexity Ladder

| Dataset | Complexity | Status | Atlas ingestion profile | Graph nature | Query file | Source |
|---|---:|---|---|---|---|---|
| `baseline_curated` | 1 | measured | `baseline_curated` | Mostly textual retrieval with a few multi-hop and exact-keyword prompts. | [`demo/queries.yaml`](../demo/queries.yaml) | https://huggingface.co/datasets/yixuantt/MultiHopRAG |
| `graph_native` | 2 | measured | `graph_native` | Explicit entity and relationship bullets over AI, antitrust, crypto, regulators, witnesses, and timelines. | [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml) | corpus/graph_native |
| `stark_prime` | 3 | candidate | `stark_prime` | Biomedical entity retrieval over diseases, drugs, genes, pathways, proteins, phenotypes, and textual descriptions. | [`demo/stark_prime_queries.yaml`](../demo/stark_prime_queries.yaml) | https://github.com/snap-stanford/stark |
| `stark_mag` | 4 | candidate | `stark_mag` | Paper, author, venue, field, citation, and affiliation retrieval where query constraints mix text with graph relations. | [`demo/stark_mag_queries.yaml`](../demo/stark_mag_queries.yaml) | https://stark.stanford.edu/ |
| `openalex_scholarly` | 5 | candidate | `openalex_scholarly` | Real scholarly graph with works, authors, institutions, concepts, citations, venues, and abstracts. | [`demo/openalex_scholarly_queries.yaml`](../demo/openalex_scholarly_queries.yaml) | https://developers.openalex.org/ |
| `gdelt_events` | 6 | candidate | `gdelt_events` | Event, actor, location, theme, source, tone, and timeline graph over real news events. | [`demo/gdelt_events_queries.yaml`](../demo/gdelt_events_queries.yaml) | https://www.gdeltproject.org/ |
| `cyber_threat_intel` | 7 | measured | `cyber_threat_intel` | Intrusion groups, campaigns, malware, tools, ATT&CK techniques, mitigations, and explicit uses/mitigates relationships. | [`demo/cyber_threat_intel_queries.yaml`](../demo/cyber_threat_intel_queries.yaml) | https://attack.mitre.org/ |

## 2. Judge-Panel Ranking Drift by Input Dataset

| Dataset | Complexity | Status | Winner | Ranking |
|---|---:|---|---|---|
| `baseline_curated` | 1 | measured | vanilla-rag | vanilla-rag 4.17 > hybrid-rag 4.00 > contextual-rag 3.92 > lazy-graph-rag 3.92 > graph-rag 3.75 > n8n-adaptive-rag 3.33 > agentic-rag 2.67 |
| `graph_native` | 2 | measured | lazy-graph-rag | lazy-graph-rag 4.31 > contextual-rag 4.19 > vanilla-rag 4.06 > hybrid-rag 3.62 > graph-rag 2.62 > agentic-rag 2.44 > n8n-adaptive-rag 2.44 |
| `stark_prime` | 3 | candidate | pending live run | pending live run |
| `stark_mag` | 4 | candidate | pending live run | pending live run |
| `openalex_scholarly` | 5 | candidate | pending live run | pending live run |
| `gdelt_events` | 6 | candidate | pending live run | pending live run |
| `cyber_threat_intel` | 7 | measured | contextual-rag | contextual-rag 3.17 > agentic-rag 3.00 > lazy-graph-rag 3.00 > n8n-adaptive-rag 3.00 > vanilla-rag 3.00 > hybrid-rag 2.92 > graph-rag 2.42 |

## 3. Flavor-Tier Tuning Results

Flavor aliases are ranked separately from base families. They reuse the
same dataset ingestion and graph state, so this tier measures query-time
parameter choices without allowing several variants of one architecture to
occupy the base-family leaderboard.

| Dataset | Status | Flavor winner | Flavor ranking |
|---|---|---|---|
| `baseline_curated` | measured | lazy-graph-rag-wide | lazy-graph-rag-wide 4.58 > hybrid-rag-fast 4.08 > vanilla-rag-wide 4.08 > contextual-rag-high-recall 3.92 > graph-rag-wide 3.83 > lazy-graph-rag-fast 3.83 > hybrid-rag-high-recall 3.75 > lazy-graph-rag-balanced 3.75 > graph-rag-fast 3.67 > graph-rag-rerank 3.67 > n8n-adaptive-rag-default 3.17 > agentic-rag-deeper 2.92 |
| `graph_native` | measured | hybrid-rag-high-recall | hybrid-rag-high-recall 4.19 > vanilla-rag-wide 4.00 > lazy-graph-rag-balanced 3.69 > lazy-graph-rag-wide 3.69 > hybrid-rag-fast 3.62 > lazy-graph-rag-fast 3.62 > contextual-rag-high-recall 3.38 > graph-rag-wide 2.62 > graph-rag-rerank 2.44 > n8n-adaptive-rag-default 2.38 > agentic-rag-deeper 2.25 > graph-rag-fast 2.06 |
| `stark_prime` | candidate | pending fresh flavor run | pending fresh flavor run |
| `stark_mag` | candidate | pending fresh flavor run | pending fresh flavor run |
| `openalex_scholarly` | candidate | pending fresh flavor run | pending fresh flavor run |
| `gdelt_events` | candidate | pending fresh flavor run | pending fresh flavor run |
| `cyber_threat_intel` | measured | hybrid-rag-fast | hybrid-rag-fast 3.67 > contextual-rag-high-recall 3.50 > hybrid-rag-high-recall 3.33 > lazy-graph-rag-fast 3.33 > lazy-graph-rag-balanced 3.00 > vanilla-rag-wide 3.00 > lazy-graph-rag-wide 2.92 > n8n-adaptive-rag-default 2.58 > agentic-rag-deeper 2.42 > graph-rag-rerank 2.42 > graph-rag-wide 2.17 > graph-rag-fast 1.92 |

### 3.1 Flavor Per-Query Winners

| Dataset | Query | Winner | Top 3 mean scores |
|---|---|---|---|
| `baseline_curated` | `keyword` | graph-rag-wide | agentic-rag-deeper 5.00 > contextual-rag-high-recall 5.00 > graph-rag-fast 5.00 |
| `baseline_curated` | `thematic` | lazy-graph-rag-wide | lazy-graph-rag-wide 5.00 > hybrid-rag-fast 4.50 > vanilla-rag-wide 4.50 |
| `baseline_curated` | `multihop` | graph-rag-wide | graph-rag-wide 4.50 > graph-rag-fast 3.00 > lazy-graph-rag-wide 3.00 |
| `baseline_curated` | `factoid` | n8n-adaptive-rag-default | contextual-rag-high-recall 5.00 > graph-rag-fast 5.00 > graph-rag-rerank 5.00 |
| `baseline_curated` | `context_starved` | graph-rag-wide | agentic-rag-deeper 5.00 > graph-rag-fast 5.00 > graph-rag-rerank 5.00 |
| `baseline_curated` | `mixed_batch` | lazy-graph-rag-fast | contextual-rag-high-recall 5.00 > hybrid-rag-fast 5.00 > hybrid-rag-high-recall 5.00 |
| `graph_native` | `entity_bridge` | graph-rag-wide | graph-rag-wide 5.00 > hybrid-rag-fast 5.00 > hybrid-rag-high-recall 5.00 |
| `graph_native` | `relationship_chain` | vanilla-rag-wide | contextual-rag-high-recall 5.00 > hybrid-rag-fast 5.00 > hybrid-rag-high-recall 5.00 |
| `graph_native` | `shared_actor` | graph-rag-rerank | graph-rag-rerank 4.50 > lazy-graph-rag-fast 3.50 > agentic-rag-deeper 3.00 |
| `graph_native` | `timeline_cause` | lazy-graph-rag-wide | lazy-graph-rag-wide 5.00 > contextual-rag-high-recall 4.50 > hybrid-rag-high-recall 4.50 |
| `graph_native` | `witness_network` | vanilla-rag-wide | hybrid-rag-high-recall 3.50 > lazy-graph-rag-balanced 3.50 > lazy-graph-rag-wide 3.50 |
| `graph_native` | `cloud_model_competition` | hybrid-rag-high-recall | hybrid-rag-high-recall 5.00 > agentic-rag-deeper 2.50 > contextual-rag-high-recall 2.50 |
| `graph_native` | `default_search_ecosystem` | lazy-graph-rag-fast | contextual-rag-high-recall 5.00 > hybrid-rag-high-recall 5.00 > lazy-graph-rag-balanced 5.00 |
| `graph_native` | `cross_domain_regulators` | vanilla-rag-wide | vanilla-rag-wide 5.00 > graph-rag-rerank 3.00 > hybrid-rag-fast 3.00 |
| `cyber_threat_intel` | `cyber_group_technique_software_chain` | hybrid-rag-high-recall | hybrid-rag-high-recall 4.50 > lazy-graph-rag-wide 4.50 > contextual-rag-high-recall 4.00 |
| `cyber_threat_intel` | `cyber_credential_access_path` | hybrid-rag-fast | hybrid-rag-fast 4.50 > contextual-rag-high-recall 4.00 > hybrid-rag-high-recall 4.00 |
| `cyber_threat_intel` | `cyber_campaign_overlap` | hybrid-rag-fast | hybrid-rag-fast 5.00 > contextual-rag-high-recall 4.00 > lazy-graph-rag-fast 3.50 |
| `cyber_threat_intel` | `cyber_mitigation_coverage` | lazy-graph-rag-fast | hybrid-rag-fast 3.50 > lazy-graph-rag-balanced 3.50 > lazy-graph-rag-fast 3.50 |
| `cyber_threat_intel` | `cyber_campaign_timeline_context` | lazy-graph-rag-balanced | lazy-graph-rag-balanced 4.00 > contextual-rag-high-recall 3.00 > hybrid-rag-fast 3.00 |
| `cyber_threat_intel` | `cyber_protocol_and_web_mitigation_path` | vanilla-rag-wide | vanilla-rag-wide 5.00 > hybrid-rag-high-recall 4.00 > lazy-graph-rag-fast 4.00 |

## 4. Canonical Evaluation Metrics

These columns come from the append-safe evidence rows. Ragas values are
evaluator-model scores, latency and failures are operational measurements,
and coverage is shown beside every ranking so unevaluable or failed cells
cannot disappear from the comparison.

| Dataset | Faithfulness ranking | Answer relevancy ranking | Latency ranking | Row coverage | Failures |
|---|---|---|---|---|---|
| `baseline_curated` | vanilla-rag 0.672 (6/6) > agentic-rag 0.664 (5/6) > hybrid-rag 0.645 (6/6) > lazy-graph-rag 0.636 (5/6) > n8n-adaptive-rag 0.564 (5/6) > contextual-rag 0.300 (5/6) | contextual-rag 0.894 (6/6) > hybrid-rag 0.869 (6/6) > lazy-graph-rag 0.858 (6/6) > graph-rag 0.842 (6/6) > n8n-adaptive-rag 0.733 (6/6) > vanilla-rag 0.708 (6/6) > agentic-rag 0.567 (6/6) | n8n-adaptive-rag 2798 ms (6/6) > vanilla-rag 3834 ms (6/6) > lazy-graph-rag 5514 ms (6/6) > agentic-rag 10774 ms (6/6) > graph-rag 12612 ms (6/6) > hybrid-rag 17683 ms (6/6) > contextual-rag 18016 ms (6/6) | 42/42 successful | 0 errors, 0 timeouts |
| `graph_native` | contextual-rag 0.607 (5/8) > lazy-graph-rag 0.416 (5/8) > hybrid-rag 0.303 (6/8) > vanilla-rag 0.279 (5/8) > agentic-rag 0.000 (1/8) > n8n-adaptive-rag 0.000 (1/8) | hybrid-rag 0.859 (8/8) > vanilla-rag 0.851 (8/8) > contextual-rag 0.841 (8/8) > lazy-graph-rag 0.829 (8/8) > graph-rag 0.796 (8/8) > agentic-rag 0.740 (8/8) > n8n-adaptive-rag 0.740 (8/8) | vanilla-rag 4539 ms (8/8) > lazy-graph-rag 4936 ms (8/8) > n8n-adaptive-rag 5299 ms (8/8) > hybrid-rag 9809 ms (8/8) > contextual-rag 11197 ms (8/8) > graph-rag 12474 ms (8/8) > agentic-rag 29113 ms (8/8) | 56/56 successful | 0 errors, 0 timeouts |
| `stark_prime` | not measured | not measured | not measured | not available | not available |
| `stark_mag` | not measured | not measured | not measured | not available | not available |
| `openalex_scholarly` | not measured | not measured | not measured | not available | not available |
| `gdelt_events` | not measured | not measured | not measured | not available | not available |
| `cyber_threat_intel` | contextual-rag 0.232 (2/6) > agentic-rag 0.224 (3/6) > n8n-adaptive-rag 0.224 (3/6) > lazy-graph-rag 0.121 (3/6) > vanilla-rag 0.052 (3/6) > hybrid-rag 0.000 (3/6) | contextual-rag 0.891 (6/6) > hybrid-rag 0.878 (6/6) > agentic-rag 0.877 (6/6) > n8n-adaptive-rag 0.877 (6/6) > lazy-graph-rag 0.873 (6/6) > vanilla-rag 0.819 (6/6) > graph-rag 0.780 (6/6) | lazy-graph-rag 8123 ms (6/6) > vanilla-rag 8907 ms (6/6) > n8n-adaptive-rag 11067 ms (6/6) > graph-rag 21203 ms (6/6) > hybrid-rag 22721 ms (6/6) > contextual-rag 24200 ms (6/6) > agentic-rag 41858 ms (6/6) | 42/42 successful | 0 errors, 0 timeouts |

## 5. Base-Family Per-Query Winners

The **Winner** column is the judge panel's `observed_winner`: the approach with the
highest mean score, breaking ties by best-answer votes. The **Top 3 mean scores**
column ranks by mean only (ties ordered by name), so when several approaches tie on
mean the vote-decided winner can fall outside the listed top three.

| Dataset | Query | Winner | Top 3 mean scores |
|---|---|---|---|
| `baseline_curated` | `keyword` | graph-rag | agentic-rag 5.00 > contextual-rag 5.00 > graph-rag 5.00 |
| `baseline_curated` | `thematic` | hybrid-rag | contextual-rag 3.50 > hybrid-rag 3.50 > vanilla-rag 3.50 |
| `baseline_curated` | `multihop` | graph-rag | graph-rag 3.00 > agentic-rag 2.50 > n8n-adaptive-rag 2.50 |
| `baseline_curated` | `factoid` | graph-rag | contextual-rag 5.00 > graph-rag 5.00 > hybrid-rag 5.00 |
| `baseline_curated` | `context_starved` | graph-rag | agentic-rag 5.00 > graph-rag 5.00 > n8n-adaptive-rag 5.00 |
| `baseline_curated` | `mixed_batch` | lazy-graph-rag | lazy-graph-rag 5.00 > hybrid-rag 4.50 > vanilla-rag 4.50 |
| `graph_native` | `entity_bridge` | vanilla-rag | vanilla-rag 5.00 > agentic-rag 4.50 > n8n-adaptive-rag 4.50 |
| `graph_native` | `relationship_chain` | vanilla-rag | lazy-graph-rag 5.00 > vanilla-rag 5.00 > contextual-rag 4.50 |
| `graph_native` | `shared_actor` | vanilla-rag | vanilla-rag 4.50 > hybrid-rag 4.00 > lazy-graph-rag 4.00 |
| `graph_native` | `timeline_cause` | hybrid-rag | hybrid-rag 5.00 > contextual-rag 4.50 > lazy-graph-rag 4.50 |
| `graph_native` | `witness_network` | contextual-rag | contextual-rag 4.50 > lazy-graph-rag 4.50 > agentic-rag 3.00 |
| `graph_native` | `cloud_model_competition` | contextual-rag | contextual-rag 4.50 > hybrid-rag 3.50 > vanilla-rag 3.50 |
| `graph_native` | `default_search_ecosystem` | lazy-graph-rag | contextual-rag 5.00 > lazy-graph-rag 5.00 > vanilla-rag 4.00 |
| `graph_native` | `cross_domain_regulators` | lazy-graph-rag | lazy-graph-rag 4.50 > contextual-rag 3.00 > hybrid-rag 3.00 |
| `cyber_threat_intel` | `cyber_group_technique_software_chain` | contextual-rag | contextual-rag 5.00 > lazy-graph-rag 4.00 > vanilla-rag 3.50 |
| `cyber_threat_intel` | `cyber_credential_access_path` | hybrid-rag | hybrid-rag 5.00 > agentic-rag 3.00 > n8n-adaptive-rag 3.00 |
| `cyber_threat_intel` | `cyber_campaign_overlap` | contextual-rag | contextual-rag 4.50 > agentic-rag 4.00 > n8n-adaptive-rag 4.00 |
| `cyber_threat_intel` | `cyber_mitigation_coverage` | vanilla-rag | vanilla-rag 4.50 > lazy-graph-rag 3.50 > agentic-rag 2.50 |
| `cyber_threat_intel` | `cyber_campaign_timeline_context` | lazy-graph-rag | lazy-graph-rag 3.50 > contextual-rag 3.00 > agentic-rag 2.50 |
| `cyber_threat_intel` | `cyber_protocol_and_web_mitigation_path` | hybrid-rag | hybrid-rag 5.00 > graph-rag 3.50 > agentic-rag 3.00 |

## 6. Interpretation

The current measured ladder has 3 rungs. On `baseline_curated`, `vanilla-rag` leads; on `graph_native`, `lazy-graph-rag` leads; on `cyber_threat_intel`, `contextual-rag` leads. `graph-rag` is measured end to end across the live rungs but does not lead any of them.

That tells us the next step is not simply adding more documents; it is adding
datasets whose native task requires relational retrieval, temporal event
reasoning, and multi-hop graph paths.

The candidate rungs are intentionally heavier: STaRK-Prime and STaRK-MAG
are semi-structured retrieval benchmarks; OpenAlex adds a real scholarly
citation/author/institution graph; GDELT adds event-time actor/location
graphs; and the measured cyber slice adds threat-technique, software,
campaign, intrusion-group, and mitigation relationships. Scores for
candidate rungs should be added only after live
matrix and judge runs produce committed snapshots.

## 7. Candidate Dataset Sources

- STaRK: semi-structured textual + relational retrieval benchmark with Amazon, MAG, and Prime domains.
- OpenAlex: CC0 scholarly graph of works, authors, institutions, concepts, venues, and citations.
- GDELT: global event/news graph with actors, events, locations, themes, sources, and timelines.
- MITRE ATT&CK: measured bounded cyber graph over intrusion groups, campaigns, software, techniques, and mitigations.
