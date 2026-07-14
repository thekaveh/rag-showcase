# 5.3 Dataset Complexity Report

This report tracks approach rankings by input dataset, ordered from the
simplest curated corpus to increasingly graph-heavy real-world candidates.
It deliberately reports by dataset rather than by vector/graph collection,
because the comparison question is how each RAG approach behaves as the
input problem becomes more relational, temporal, and multi-hop.
Each row also names the Atlas ingestion profile whose revision and job id
are stored with newly generated matrix and judgment snapshots.

For the run protocol, model roles, approach invocation details, and
judge-panel design, see [`evaluation-methodology.md`](evaluation-methodology.md).
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
| `baseline_curated` | 1 | measured | n8n-adaptive-rag | n8n-adaptive-rag 4.42 > vanilla-rag 4.42 > hybrid-rag 4.08 > lazy-graph-rag 3.92 > contextual-rag 3.67 > graph-rag 3.00 > agentic-rag 2.33 |
| `graph_native` | 2 | measured | contextual-rag | contextual-rag 4.12 > lazy-graph-rag 3.88 > hybrid-rag 3.62 > n8n-adaptive-rag 3.62 > vanilla-rag 3.62 > agentic-rag 2.38 > graph-rag 2.38 |
| `stark_prime` | 3 | candidate | pending live run | pending live run |
| `stark_mag` | 4 | candidate | pending live run | pending live run |
| `openalex_scholarly` | 5 | candidate | pending live run | pending live run |
| `gdelt_events` | 6 | candidate | pending live run | pending live run |
| `cyber_threat_intel` | 7 | measured | lazy-graph-rag | lazy-graph-rag 3.25 > contextual-rag 3.17 > hybrid-rag 3.17 > n8n-adaptive-rag 2.67 > vanilla-rag 2.67 > agentic-rag 1.67 > graph-rag 1.50 |

## 3. Canonical Evaluation Metrics

These columns come from the append-safe evidence rows. Ragas values are
evaluator-model scores, latency and failures are operational measurements,
and coverage is shown beside every ranking so unevaluable or failed cells
cannot disappear from the comparison.

| Dataset | Faithfulness ranking | Answer relevancy ranking | Latency ranking | Row coverage | Failures |
|---|---|---|---|---|---|
| `baseline_curated` | not evaluated | not evaluated | n8n-adaptive-rag 2226 ms (6/6) > vanilla-rag 4281 ms (6/6) > lazy-graph-rag 5118 ms (6/6) > hybrid-rag 19421 ms (6/6) > contextual-rag 19752 ms (6/6) > agentic-rag 35909 ms (6/6) > graph-rag 67392 ms (6/6) | 42/42 successful | 0 errors, 0 timeouts |
| `graph_native` | not evaluated | not evaluated | n8n-adaptive-rag 2372 ms (8/8) > vanilla-rag 4771 ms (8/8) > lazy-graph-rag 6074 ms (8/8) > hybrid-rag 10384 ms (8/8) > contextual-rag 11852 ms (8/8) > graph-rag 88034 ms (8/8) > agentic-rag 141717 ms (8/8) | 56/56 successful | 0 errors, 0 timeouts |
| `stark_prime` | not measured | not measured | not measured | not available | not available |
| `stark_mag` | not measured | not measured | not measured | not available | not available |
| `openalex_scholarly` | not measured | not measured | not measured | not available | not available |
| `gdelt_events` | not measured | not measured | not measured | not available | not available |
| `cyber_threat_intel` | not evaluated | not evaluated | n8n-adaptive-rag 1991 ms (6/6) > vanilla-rag 9281 ms (6/6) > lazy-graph-rag 11946 ms (6/6) > contextual-rag 24520 ms (6/6) > hybrid-rag 25661 ms (6/6) > graph-rag 67607 ms (6/6) > agentic-rag 204667 ms (6/6) | 42/42 successful | 0 errors, 0 timeouts |

## 4. Per-Query Winners

The **Winner** column is the judge panel's `observed_winner`: the approach with the
highest mean score, breaking ties by best-answer votes. The **Top 3 mean scores**
column ranks by mean only (ties ordered by name), so when several approaches tie on
mean the vote-decided winner can fall outside the listed top three.

| Dataset | Query | Winner | Top 3 mean scores |
|---|---|---|---|
| `baseline_curated` | `keyword` | graph-rag | graph-rag 5.00 > agentic-rag 4.50 > contextual-rag 4.50 |
| `baseline_curated` | `thematic` | hybrid-rag | hybrid-rag 4.50 > n8n-adaptive-rag 4.00 > vanilla-rag 4.00 |
| `baseline_curated` | `multihop` | n8n-adaptive-rag | n8n-adaptive-rag 3.50 > vanilla-rag 3.50 > contextual-rag 2.50 |
| `baseline_curated` | `factoid` | graph-rag | contextual-rag 5.00 > graph-rag 5.00 > hybrid-rag 5.00 |
| `baseline_curated` | `context_starved` | graph-rag | agentic-rag 5.00 > graph-rag 5.00 > contextual-rag 4.50 |
| `baseline_curated` | `mixed_batch` | n8n-adaptive-rag | lazy-graph-rag 5.00 > n8n-adaptive-rag 5.00 > vanilla-rag 5.00 |
| `graph_native` | `entity_bridge` | vanilla-rag | n8n-adaptive-rag 5.00 > vanilla-rag 5.00 > contextual-rag 4.00 |
| `graph_native` | `relationship_chain` | n8n-adaptive-rag | contextual-rag 5.00 > hybrid-rag 5.00 > lazy-graph-rag 5.00 |
| `graph_native` | `shared_actor` | agentic-rag | agentic-rag 4.00 > contextual-rag 3.50 > graph-rag 3.50 |
| `graph_native` | `timeline_cause` | hybrid-rag | hybrid-rag 5.00 > contextual-rag 4.50 > lazy-graph-rag 4.50 |
| `graph_native` | `witness_network` | contextual-rag | contextual-rag 3.00 > lazy-graph-rag 3.00 > agentic-rag 2.50 |
| `graph_native` | `cloud_model_competition` | contextual-rag | contextual-rag 4.50 > hybrid-rag 3.50 > n8n-adaptive-rag 3.50 |
| `graph_native` | `default_search_ecosystem` | lazy-graph-rag | contextual-rag 5.00 > lazy-graph-rag 5.00 > n8n-adaptive-rag 4.00 |
| `graph_native` | `cross_domain_regulators` | lazy-graph-rag | lazy-graph-rag 4.50 > contextual-rag 3.50 > hybrid-rag 3.50 |
| `cyber_threat_intel` | `cyber_group_technique_software_chain` | contextual-rag | contextual-rag 4.50 > lazy-graph-rag 3.50 > n8n-adaptive-rag 3.00 |
| `cyber_threat_intel` | `cyber_credential_access_path` | hybrid-rag | graph-rag 4.00 > hybrid-rag 4.00 > agentic-rag 3.50 |
| `cyber_threat_intel` | `cyber_campaign_overlap` | contextual-rag | contextual-rag 5.00 > lazy-graph-rag 4.00 > hybrid-rag 3.50 |
| `cyber_threat_intel` | `cyber_mitigation_coverage` | lazy-graph-rag | lazy-graph-rag 4.50 > n8n-adaptive-rag 3.50 > vanilla-rag 3.50 |
| `cyber_threat_intel` | `cyber_campaign_timeline_context` | lazy-graph-rag | lazy-graph-rag 3.50 > contextual-rag 2.00 > hybrid-rag 2.00 |
| `cyber_threat_intel` | `cyber_protocol_and_web_mitigation_path` | hybrid-rag | hybrid-rag 5.00 > contextual-rag 2.50 > lazy-graph-rag 2.50 |

## 5. Interpretation

The current measured ladder has 3 rungs. On `baseline_curated`, `n8n-adaptive-rag` leads; on `graph_native`, `contextual-rag` leads; on `cyber_threat_intel`, `lazy-graph-rag` leads. `graph-rag` is measured end to end across the live rungs but does not lead any of them.

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

## 6. Candidate Dataset Sources

- STaRK: semi-structured textual + relational retrieval benchmark with Amazon, MAG, and Prime domains.
- OpenAlex: CC0 scholarly graph of works, authors, institutions, concepts, venues, and citations.
- GDELT: global event/news graph with actors, events, locations, themes, sources, and timelines.
- MITRE ATT&CK: measured bounded cyber graph over intrusion groups, campaigns, software, techniques, and mitigations.
