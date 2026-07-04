# Dataset Complexity Report

This report tracks approach rankings by input dataset, ordered from the
simplest curated corpus to increasingly graph-heavy real-world candidates.
It deliberately reports by dataset rather than by vector/graph collection,
because the comparison question is how each RAG approach behaves as the
input problem becomes more relational, temporal, and multi-hop.

For the run protocol, model roles, approach invocation details, and
judge-panel design, see [`evaluation-methodology.md`](evaluation-methodology.md).
For approach-by-approach internals and tuning surfaces, see
[`approaches.md`](approaches.md).

## 1. Dataset Complexity Ladder

| Dataset | Complexity | Status | Graph nature | Query file | Source |
|---|---:|---|---|---|---|
| `baseline_curated` | 1 | measured | Mostly textual retrieval with a few multi-hop and exact-keyword prompts. | [`demo/queries.yaml`](../demo/queries.yaml) | https://huggingface.co/datasets/yixuantt/MultiHopRAG |
| `graph_native` | 2 | measured | Explicit entity and relationship bullets over AI, antitrust, crypto, regulators, witnesses, and timelines. | [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml) | corpus/graph_native |
| `stark_prime` | 3 | candidate | Biomedical entity retrieval over diseases, drugs, genes, pathways, proteins, phenotypes, and textual descriptions. | [`demo/stark_prime_queries.yaml`](../demo/stark_prime_queries.yaml) | https://github.com/snap-stanford/stark |
| `stark_mag` | 4 | candidate | Paper, author, venue, field, citation, and affiliation retrieval where query constraints mix text with graph relations. | [`demo/stark_mag_queries.yaml`](../demo/stark_mag_queries.yaml) | https://stark.stanford.edu/ |
| `openalex_scholarly` | 5 | candidate | Real scholarly graph with works, authors, institutions, concepts, citations, venues, and abstracts. | [`demo/openalex_scholarly_queries.yaml`](../demo/openalex_scholarly_queries.yaml) | https://developers.openalex.org/ |
| `gdelt_events` | 6 | candidate | Event, actor, location, theme, source, tone, and timeline graph over real news events. | [`demo/gdelt_events_queries.yaml`](../demo/gdelt_events_queries.yaml) | https://www.gdeltproject.org/ |
| `cyber_threat_intel` | 7 | measured | Intrusion groups, campaigns, malware, tools, ATT&CK techniques, mitigations, and explicit uses/mitigates relationships. | [`demo/cyber_threat_intel_queries.yaml`](../demo/cyber_threat_intel_queries.yaml) | https://attack.mitre.org/ |

## 2. Ranking Drift by Input Dataset

| Dataset | Complexity | Status | Winner | Ranking |
|---|---:|---|---|---|
| `baseline_curated` | 1 | measured | vanilla-rag-wide | vanilla-rag-wide 4.42 > n8n-adaptive-rag 4.25 > n8n-adaptive-rag-default 4.25 > vanilla-rag 4.25 > contextual-rag 4.08 > contextual-rag-high-recall 4.08 > hybrid-rag 4.08 > hybrid-rag-fast 4.08 > hybrid-rag-high-recall 4.08 > graph-rag-fast 3.92 > graph-rag 3.42 > agentic-rag-deeper 3.08 > agentic-rag 2.67 > graph-rag-wide 1.00 |
| `graph_native` | 2 | measured | hybrid-rag-high-recall | hybrid-rag-high-recall 4.25 > contextual-rag 3.94 > hybrid-rag 3.88 > vanilla-rag-wide 3.75 > n8n-adaptive-rag 3.56 > graph-rag-fast 3.44 > hybrid-rag-fast 3.44 > n8n-adaptive-rag-default 3.38 > vanilla-rag 3.38 > contextual-rag-high-recall 3.25 > agentic-rag-deeper 2.94 > graph-rag 2.75 > agentic-rag 2.62 > graph-rag-wide 1.38 |
| `stark_prime` | 3 | candidate | pending live run | pending live run |
| `stark_mag` | 4 | candidate | pending live run | pending live run |
| `openalex_scholarly` | 5 | candidate | pending live run | pending live run |
| `gdelt_events` | 6 | candidate | pending live run | pending live run |
| `cyber_threat_intel` | 7 | measured | contextual-rag-high-recall | contextual-rag-high-recall 3.58 > contextual-rag 3.17 > n8n-adaptive-rag 3.08 > n8n-adaptive-rag-default 3.08 > vanilla-rag 3.08 > hybrid-rag-fast 2.92 > hybrid-rag-high-recall 2.92 > vanilla-rag-wide 2.83 > hybrid-rag 2.50 > graph-rag-fast 2.42 > agentic-rag-deeper 2.08 > agentic-rag 2.00 > graph-rag 1.92 > graph-rag-wide 1.00 |

## 3. Per-Query Winners

The **Winner** column is the judge panel's `observed_winner`: the approach with the
highest mean score, breaking ties by best-answer votes. The **Top 3 mean scores**
column ranks by mean only (ties ordered by name), so when several approaches tie on
mean the vote-decided winner can fall outside the listed top three.

| Dataset | Query | Winner | Top 3 mean scores |
|---|---|---|---|
| `baseline_curated` | `keyword` | graph-rag-fast | agentic-rag 5.00 > agentic-rag-deeper 5.00 > contextual-rag-high-recall 5.00 |
| `baseline_curated` | `thematic` | vanilla-rag-wide | vanilla-rag-wide 5.00 > n8n-adaptive-rag 4.00 > n8n-adaptive-rag-default 4.00 |
| `baseline_curated` | `multihop` | hybrid-rag-high-recall | hybrid-rag-high-recall 3.50 > contextual-rag 3.00 > graph-rag-fast 3.00 |
| `baseline_curated` | `factoid` | graph-rag-fast | contextual-rag 5.00 > contextual-rag-high-recall 5.00 > graph-rag 5.00 |
| `baseline_curated` | `context_starved` | agentic-rag | agentic-rag 5.00 > agentic-rag-deeper 5.00 > graph-rag 5.00 |
| `baseline_curated` | `mixed_batch` | hybrid-rag-fast | contextual-rag 5.00 > contextual-rag-high-recall 5.00 > hybrid-rag 5.00 |
| `graph_native` | `entity_bridge` | graph-rag-fast | graph-rag-fast 5.00 > contextual-rag 4.50 > contextual-rag-high-recall 4.50 |
| `graph_native` | `relationship_chain` | n8n-adaptive-rag | hybrid-rag 5.00 > hybrid-rag-fast 5.00 > hybrid-rag-high-recall 5.00 |
| `graph_native` | `shared_actor` | contextual-rag | contextual-rag 3.50 > graph-rag-fast 3.00 > hybrid-rag 3.00 |
| `graph_native` | `timeline_cause` | vanilla-rag-wide | hybrid-rag-fast 5.00 > hybrid-rag-high-recall 5.00 > n8n-adaptive-rag 5.00 |
| `graph_native` | `witness_network` | agentic-rag-deeper | agentic-rag 5.00 > agentic-rag-deeper 5.00 > graph-rag-fast 4.00 |
| `graph_native` | `cloud_model_competition` | contextual-rag | contextual-rag 5.00 > hybrid-rag 5.00 > hybrid-rag-high-recall 5.00 |
| `graph_native` | `default_search_ecosystem` | hybrid-rag-fast | contextual-rag 5.00 > hybrid-rag 5.00 > hybrid-rag-fast 5.00 |
| `graph_native` | `cross_domain_regulators` | vanilla-rag-wide | vanilla-rag-wide 5.00 > contextual-rag-high-recall 4.50 > hybrid-rag-high-recall 4.50 |
| `cyber_threat_intel` | `cyber_group_technique_software_chain` | contextual-rag-high-recall | contextual-rag-high-recall 5.00 > contextual-rag 4.50 > hybrid-rag-high-recall 4.50 |
| `cyber_threat_intel` | `cyber_credential_access_path` | vanilla-rag | n8n-adaptive-rag 5.00 > n8n-adaptive-rag-default 5.00 > vanilla-rag 5.00 |
| `cyber_threat_intel` | `cyber_campaign_overlap` | contextual-rag-high-recall | contextual-rag-high-recall 5.00 > contextual-rag 3.50 > graph-rag 3.50 |
| `cyber_threat_intel` | `cyber_mitigation_coverage` | agentic-rag-deeper | agentic-rag-deeper 4.00 > hybrid-rag-fast 4.00 > contextual-rag-high-recall 3.50 |
| `cyber_threat_intel` | `cyber_campaign_timeline_context` | contextual-rag | contextual-rag 3.00 > n8n-adaptive-rag 2.50 > n8n-adaptive-rag-default 2.50 |
| `cyber_threat_intel` | `cyber_protocol_and_web_mitigation_path` | hybrid-rag | hybrid-rag 5.00 > n8n-adaptive-rag 4.00 > n8n-adaptive-rag-default 4.00 |

## 4. Interpretation

The current measured ladder has 3 rungs. On `baseline_curated`, `vanilla-rag-wide` leads; on `graph_native`, `hybrid-rag-high-recall` leads; on `cyber_threat_intel`, `contextual-rag-high-recall` leads. `graph-rag` is measured end to end across the live rungs but does not lead any of them.

That tells us the next step is not simply adding more documents; it is adding
datasets whose native task requires relational retrieval, temporal event
reasoning, and multi-hop graph paths.

The live flavor snapshots show one clear tuning result: `graph-rag-wide` ranked last on every measured dataset. Its committed answers are frequently truncated one-token or heading-only output — the wide retrieval envelope overflows the current LightRAG query setup. `graph-rag-fast` was the stronger graph flavor, winning 3 individual queries across the measured datasets while reducing latency.

The candidate rungs are intentionally heavier: STaRK-Prime and STaRK-MAG
are semi-structured retrieval benchmarks; OpenAlex adds a real scholarly
citation/author/institution graph; GDELT adds event-time actor/location
graphs; and the measured cyber slice adds threat-technique, software,
campaign, intrusion-group, and mitigation relationships. Scores for
candidate rungs should be added only after live
matrix and judge runs produce committed snapshots.

## 5. Candidate Dataset Sources

- STaRK: semi-structured textual + relational retrieval benchmark with Amazon, MAG, and Prime domains.
- OpenAlex: CC0 scholarly graph of works, authors, institutions, concepts, venues, and citations.
- GDELT: global event/news graph with actors, events, locations, themes, sources, and timelines.
- MITRE ATT&CK: measured bounded cyber graph over intrusion groups, campaigns, software, techniques, and mitigations.
