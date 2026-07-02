# Dataset Complexity Report

This report tracks approach rankings by input dataset, ordered from the
simplest curated corpus to increasingly graph-heavy real-world candidates.
It deliberately reports by dataset rather than by vector/graph collection,
because the comparison question is how each RAG approach behaves as the
input problem becomes more relational, temporal, and multi-hop.

## 1. Dataset Complexity Ladder

| Dataset | Complexity | Status | Graph nature | Query file | Source |
|---|---:|---|---|---|---|
| `baseline_curated` | 1 | measured | Mostly textual retrieval with a few multi-hop and exact-keyword prompts. | [`demo/queries.yaml`](../demo/queries.yaml) | https://huggingface.co/datasets/yixuantt/MultiHopRAG |
| `graph_native` | 2 | measured | Explicit entity and relationship bullets over AI, antitrust, crypto, regulators, witnesses, and timelines. | [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml) | corpus/graph_native |
| `stark_prime` | 3 | candidate | Biomedical entity retrieval over diseases, drugs, genes, pathways, proteins, phenotypes, and textual descriptions. | [`demo/stark_prime_queries.yaml`](../demo/stark_prime_queries.yaml) | https://github.com/snap-stanford/stark |
| `stark_mag` | 4 | candidate | Paper, author, venue, field, citation, and affiliation retrieval where query constraints mix text with graph relations. | [`demo/stark_mag_queries.yaml`](../demo/stark_mag_queries.yaml) | https://stark.stanford.edu/ |
| `openalex_scholarly` | 5 | candidate | Real scholarly graph with works, authors, institutions, concepts, citations, venues, and abstracts. | [`demo/openalex_scholarly_queries.yaml`](../demo/openalex_scholarly_queries.yaml) | https://developers.openalex.org/ |
| `gdelt_events` | 6 | candidate | Event, actor, location, theme, source, tone, and timeline graph over real news events. | [`demo/gdelt_events_queries.yaml`](../demo/gdelt_events_queries.yaml) | https://www.gdeltproject.org/ |
| `cyber_threat_intel` | 7 | candidate | Threat groups, techniques, software, mitigations, CVEs, CWEs, CPE products, and campaign relationships. | [`demo/cyber_threat_intel_queries.yaml`](../demo/cyber_threat_intel_queries.yaml) | https://attack.mitre.org/ |

## 2. Ranking Drift by Input Dataset

| Dataset | Complexity | Status | Winner | Ranking |
|---|---:|---|---|---|
| `baseline_curated` | 1 | measured | contextual-rag | contextual-rag 4.50 > hybrid-rag 4.17 > n8n-adaptive-rag 4.17 > vanilla-rag 4.17 > graph-rag 3.25 > agentic-rag 2.33 |
| `graph_native` | 2 | measured | contextual-rag | contextual-rag 4.38 > n8n-adaptive-rag 3.88 > vanilla-rag 3.88 > hybrid-rag 3.69 > graph-rag 2.69 > agentic-rag 1.62 |
| `stark_prime` | 3 | candidate | pending live run | pending live run |
| `stark_mag` | 4 | candidate | pending live run | pending live run |
| `openalex_scholarly` | 5 | candidate | pending live run | pending live run |
| `gdelt_events` | 6 | candidate | pending live run | pending live run |
| `cyber_threat_intel` | 7 | candidate | pending live run | pending live run |

## 3. Interpretation

The current measured ladder has two rungs. On the baseline curated corpus,
`contextual-rag` leads, with vanilla, hybrid, and n8n close behind. On the
graph-native dossiers, `contextual-rag` still leads and `graph-rag` is
measured but not yet dominant. That tells us the next step is not simply
adding more documents; it is adding datasets whose native task requires
relational retrieval, temporal event reasoning, and multi-hop graph paths.

The candidate rungs are intentionally heavier: STaRK-Prime and STaRK-MAG
are semi-structured retrieval benchmarks; OpenAlex adds a real scholarly
citation/author/institution graph; GDELT adds event-time actor/location
graphs; and the cyber slice adds threat-technique-vulnerability-product
relationships. Scores for those rungs should be added only after live
matrix and judge runs produce committed snapshots.

## 4. Candidate Dataset Sources

- STaRK: semi-structured textual + relational retrieval benchmark with Amazon, MAG, and Prime domains.
- OpenAlex: CC0 scholarly graph of works, authors, institutions, concepts, venues, and citations.
- GDELT: global event/news graph with actors, events, locations, themes, sources, and timelines.
- MITRE ATT&CK + NVD: public cyber graph over groups, software, techniques, mitigations, CVEs, CWEs, and CPE products.
