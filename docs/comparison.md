# 5.2 RAG Approaches — Live Comparison

A side-by-side comparison of the RAG approaches in this repo, run against a live
`gen-ai-rag` Atlas stack. The recorded 2026-07-17 run used a local workstation
with host Ollama; that is run metadata, not a repo requirement. See
[`hardware.md`](hardware.md) for hardware guidance without assuming one host shape.

- **Run date:** 2026-07-17
- **Approaches compared:** all 6 canonical approaches plus explicitly selected
  experimental `lazy-graph-rag` (7 base families), followed by all 12 named
  non-base flavor aliases as a separate tier.
- **Baseline corpus:** 11-document curated corpus — a MultiHop-RAG subset plus `widget-error-codes.md`.
- **Graph-native corpus:** 10 committed relation-dense dossiers in
  [`corpus/graph_native/`](../corpus/graph_native/).
- **Cyber corpus:** 60 committed MITRE ATT&CK dossiers in
  [`corpus/cyber_threat_intel/`](../corpus/cyber_threat_intel/).
- **Queries:** baseline prompts in [`demo/queries.yaml`](../demo/queries.yaml),
  graph-native prompts in [`demo/graph_native_queries.yaml`](../demo/graph_native_queries.yaml),
  and cyber prompts in [`demo/cyber_threat_intel_queries.yaml`](../demo/cyber_threat_intel_queries.yaml).
- **Harness:** [`compare/run_matrix.py`](../compare/run_matrix.py),
  [`compare/summarize.py`](../compare/summarize.py), and
  [`compare/judge.py`](../compare/judge.py). Renewed runs write canonical evidence
  JSONL, deterministic evaluation JSON, and compatibility matrix/judgment JSON.
  Raw working outputs live under gitignored `compare/results/`; the ladder
  validated and committed matrix, judgments, canonical evidence JSONL, and
  deterministic evaluation JSON for each dataset under [`results/`](results/).
- **Methodology:** the full protocol, model-role map, judge-panel design, and
  dataset-ladder process are documented in
  [`evaluation-methodology.md`](evaluation-methodology.md).

The experimental lazy graph family remains excluded from `default`, but its base
alias was selected explicitly for this run. Its implementation, cold/warm cache
measurements, and keep-experimental decision are documented in
[`lazy-graph-rag.md`](lazy-graph-rag.md).

## 1. Headline

The renewed ladder completed all 380 answer cells on all three measured datasets
without response errors or timeouts: 140 base-family cells and 240 flavor cells.
Base winners changed with the corpus: `vanilla-rag` scored 4.17 on baseline,
experimental `lazy-graph-rag` scored 4.31 on graph-native, and `contextual-rag`
scored 3.17 on cyber. The flavor winners were `lazy-graph-rag-wide` at 4.58,
`hybrid-rag-high-recall` at 4.19, and `hybrid-rag-fast` at 3.67. Default
LightRAG remained operational and averaged 12.61, 12.47, and 21.20 seconds.

The current run depends on these integration fixes and operating choices:

- Atlas model-scoped `think:false` for the configured Qwen reasoning model;
- LightRAG role-specific EXTRACT/KEYWORD/QUERY models configured separately;
- LightRAG EXTRACT tuned to `max_async=1` and `timeout=900`;
- `nomic-embed-text` embeddings for graph ingestion;
- LightRAG upload retry on HTTP 409 backpressure, with exact already-processed
  conflicts treated as idempotent during a resumed ingest;
- TEI rerank batching for both chunk and LightRAG candidates, capped to the
  reranker's 32-item client batch limit;
- Atlas-managed LightRAG query profiles for canonical, fast, wide, and rerank
  variants, all sharing one ingested graph.

## 2. Reproduce

```bash
./scripts/start-all.sh
export JUDGE_MODELS=judge-a,judge-b
uv run python compare/run_matrix.py
uv run python compare/judge.py
```

`MATRIX_MODELS` can restrict the approaches for a partial run:

```bash
MATRIX_MODELS=vanilla-rag,graph-rag uv run python compare/run_matrix.py
```

`MATRIX_FLAVORS` expands named profiles from `compare/flavors.yaml`, which is the
benchmark-side companion to the backend `flavors.yaml` used for Open WebUI aliases:

```bash
MATRIX_FLAVORS=default,graph-rag-wide uv run python compare/run_matrix.py
```

The graph-native comparison uses the same harness with alternate input/output files:

```bash
export JUDGE_MODELS=judge-a,judge-b
MATRIX_QUERIES_FILE=demo/graph_native_queries.yaml \
MATRIX_DATASET_ID=graph_native \
MATRIX_RUN_ID=manual-graph-native \
MATRIX_RESULTS_FILE=graph_native_matrix.json \
MATRIX_CANONICAL_FILE=graph_native_evidence.jsonl \
MATRIX_SUMMARY_FILE=graph_native_evaluation.json \
uv run python compare/run_matrix.py

JUDGE_MATRIX_FILE=graph_native_matrix.json \
JUDGE_RESULTS_FILE=graph_native_judgments.json \
uv run python compare/judge.py

uv run python compare/summarize.py \
  --rows compare/results/graph_native_evidence.jsonl \
  --output compare/results/graph_native_evaluation.json \
  --csv-output compare/results/graph_native_evaluation.csv \
  --judgments compare/results/graph_native_judgments.json
```

For the dataset-by-dataset view, use the dataset manifest and report generator:

```bash
uv run python compare/report_datasets.py --output docs/dataset-complexity-report.md
```

That report is committed at [`docs/dataset-complexity-report.md`](dataset-complexity-report.md)
and is organized by input dataset complexity rather than by vector/graph collection.

The committed 2026-07-17 ladder used the end-to-end runner so every measured
dataset got a fresh ingest, LightRAG drain, matrix run, judge run, result snapshot,
manifest update, and report regeneration:

```bash
JUDGE_MODELS=qwen3.6:latest,gemma4:31b \
uv run python scripts/run-dataset-ladder.py \
  --date-stamp 2026-07-17 \
  --dataset baseline_curated \
  --dataset graph_native \
  --dataset cyber_threat_intel \
  --include-flavor-tier
```

## 3. The approaches

See the [README](../README.md#4-the-seven-approaches) for the entry table and
[`docs/approaches.md`](approaches.md) for exact internal steps, dependencies,
tuning variables, and measured behavior. In one line each:
`vanilla-rag` is dense top-k; `hybrid-rag` adds BM25 and TEI rerank;
`contextual-rag` retrieves context-prefixed chunks; `graph-rag` delegates to
LightRAG; `agentic-rag` runs a ReAct loop over vector and graph tools; and
`n8n-adaptive-rag` routes through the n8n workflow; experimental
`lazy-graph-rag` performs deterministic concept-graph expansion.

## 4. Environment

| Concern | This run |
|---|---|
| Hardware | Mac Studio M2 Ultra, 192 GB unified memory |
| Atlas | final pin `c744467e` (`v0.1.0-438-gc744467e`), project `rag-showcase`; baseline/graph-native rows record pre-rerank-fix `2229fee9`, cyber rows record `c744467e` |
| Ports | baseline and graph-native `64500-64609`; cyber `22000-22109`; both blocks were verified free at assignment |
| Provider | host Ollama selected through Atlas `ollama-localhost`; ComfyUI disabled as not applicable |
| Generation | local Ollama `qwen3.6:latest`, with Atlas-scoped `think:false` |
| LightRAG roles | EXTRACT `mistral-small3.2:24b`; KEYWORD/QUERY `qwen3.6:latest` |
| Embeddings | `nomic-embed-text`, host Ollama for LightRAG; LiteLLM embedding route for plugin vectors |
| Judges | `qwen3.6:latest` + `gemma4:31b`, local Ollama, `think:false` |

This run uses the current rag-showcase alignment to Atlas's public `LIGHTRAG_*`
role inputs. Current setup configures LightRAG through Atlas and lets Atlas/LiteLLM
decide whether model calls go to container Ollama, host Ollama, GPU container
Ollama, or another configured provider.

## 5. Findings

1. **`think:false` is mandatory for the Qwen reasoning model.** With thinking enabled,
   extraction and generation calls spend time on hidden reasoning. With `think:false`,
   the same local model is roughly 30x faster for this workload. The setting is
   is scoped per model, so it does not leak to unrelated models. The current
   baseline delegates the same model-scoped default to Atlas's model catalog.
2. **Atlas now has a first-class host-Ollama source.** The original run needed an
   ad hoc LiteLLM alias to reach host Ollama. The updated Atlas submodule exposes
   `LLM_PROVIDER_SOURCE=ollama-localhost`, so the repo no longer needs to assume
   any particular host hardware path.
3. **Atlas now exposes LightRAG role-specific model settings.** The current
   submodule maps `LIGHTRAG_EXTRACT_*`, `LIGHTRAG_KEYWORD_*`, and
   `LIGHTRAG_QUERY_*` inputs into LightRAG's native roles. Rag-showcase now sets
   those Atlas inputs instead of patching LightRAG runtime env directly.
4. **LightRAG extraction works, but graph builds remain expensive.** Fresh builds
   drained for all three corpora, including 60 cyber documents producing 66
   chunks. The cyber extraction phase dominated ladder runtime even with the
   dedicated non-reasoning extraction model.
5. **LightRAG rerank is now compatible and measured.** Atlas translates the
   LightRAG request to TEI and batches candidate lists over the 32-item service
   limit. The run exposed and fixed the missing batching case in Atlas
   [#713](https://github.com/thekaveh/atlas/issues/713) / [#714](https://github.com/thekaveh/atlas/pull/714),
   then discarded the pre-fix row and reran the complete flavor tier.
6. **`agentic-rag` is still step-limited.** `MAX_STEPS=4` is too low for several
   synthesis prompts; it does well on single-hop tool use and often stops early on
   multi-step tasks.

## 6. Current Seven-Approach Results

The 2026-07-17 ladder ran three datasets, 20 queries, and seven base approaches,
producing 140 successful base cells plus complete scores from both judges. It
then ran the same queries through all twelve non-base flavors for another 240
successful cells. Each dataset/tier has all four canonical artifacts under
[`docs/results/`](results/).

| Dataset | Cells | Winner | Judge mean | Mean latency | Current reading |
|---|---:|---|---:|---:|---|
| `baseline_curated` | 42 | `vanilla-rag` | 4.17 | 3.83 s | Direct dense retrieval remained the strongest base control. |
| `graph_native` | 56 | `lazy-graph-rag` | 4.31 | 4.94 s | Deterministic expansion won the relation-dense aggregate. |
| `cyber_threat_intel` | 42 | `contextual-rag` | 3.17 | 24.20 s | Context-prefixed chunks led; five approaches tied closely at 3.00. |

All approaches had zero response errors and zero timeouts. Atlas Ragas returned
numeric answer relevancy for every cell and coverage-aware faithfulness for rows
with exact contexts. LightRAG answer-only rows remain intentionally ineligible
for faithfulness; they are not assigned zero. The generated
[`dataset-complexity-report.md`](dataset-complexity-report.md) is the canonical
aggregate and per-query view. Flavor rankings remain separate from the base-family
leaderboard.

| Dataset | Flavor winner | Judge mean | Mean latency |
|---|---|---:|---:|
| `baseline_curated` | `lazy-graph-rag-wide` | 4.58 | 6.31 s |
| `graph_native` | `hybrid-rag-high-recall` | 4.19 | 10.23 s |
| `cyber_threat_intel` | `hybrid-rag-fast` | 3.67 | 6.98 s |

## 7. Judgment Panel

The scoring pass used `compare/judge.py`, which evaluates stored
matrix answers after all approaches have already run. Its manifest selected local
Ollama models `qwen3.6:latest` and `gemma4:31b`, both called with `temperature=0`
and `think:false`.

The panel was chosen to keep evaluation local and repeatable while avoiding a
single-model judge. For each query, the harness anonymizes and deterministically
shuffles the approach answers, gives the judges the query-specific scoring
rationale from the query YAML, asks for 1-5 scores plus a best-answer letter, and
then aggregates mean score by approach with best-answer votes as the tiebreaker.
The judgment files in `docs/results/` keep the per-judge scores, reasons, and
resolved judge backend. This published run used direct host Ollama. The checked-in
harness now defaults to the Atlas LiteLLM gateway and reads judge models, endpoint,
temperature, and optional thinking from `compare/evaluation.yaml`; environment
overrides can use another OpenAI-compatible provider without changing the runner.

## 8. Graph Findings

The renewed run shows that the graph path is technically healthy: LightRAG indexed
the baseline, graph-native, and cyber corpora, drained extraction, and answered
through the same LiteLLM/Open WebUI route as the other approaches.

The quality story is more nuanced. Default `graph-rag` won three baseline
questions and ranked fifth, fifth, then seventh by aggregate, with mean latency
of 12.61, 12.47, and 21.20 seconds. Atlas-managed profiles materially changed
both quality and latency, but no one graph profile dominated every dataset.

The rerank-enabled profile is technically healthy but remains opt-in. Against
`graph-rag-fast`, reranking produced the same baseline judge mean at 2.38x
latency, gained 0.38 judge points on graph-native with lower Ragas answer
relevancy, and gained 0.50 judge points on cyber while nearly doubling latency
and again lowering answer relevancy. Against `graph-rag-wide`, it lost judge mean
on graph-native, won on cyber, and was slower on all three rungs. The detailed
tradeoff table is in
[`approach-flavor-tuning.md`](approach-flavor-tuning.md#81-lightrag-rerank-tradeoff).

The cyber corpus is the clearest warning against assuming that a graph-shaped
input automatically favors the LLM-extracted graph endpoint. The ATT&CK docs are
highly relational, but the judges favored contextual retrieval overall. Lazy
graph won graph-native data, made zero index-time LLM calls, and was faster than
LightRAG. It remains experimental because co-occurrence
edges are untyped and its concept extractor is deliberately lightweight. See
[`lazy-graph-rag.md`](lazy-graph-rag.md) for the measured keep decision.

## 9. Caveats

- **Bounded corpora:** the scored run uses bounded corpora: 11 baseline docs,
  10 graph-native dossiers, and 60 ATT&CK cyber dossiers. Larger graph builds are
  still a separate capacity test.
- **Three rungs measured so far:** the dataset complexity report still includes
  heavier candidates such as STaRK, OpenAlex, and GDELT, but their rankings remain
  pending until live matrix and judge snapshots are produced.
- **Graph-native corpus is synthetic-curated:** the documents are real-world dossiers
  with source links and explicit relationship bullets, designed to make graph structure
  available. This is a better graph test than the baseline subset, but it is still not
  a large natural enterprise corpus.
- **Current local judges:** scores are directional, not authoritative. Answers
  are shuffled and anonymized, but the 2026-07-17 panel used two local
  models. The renewed harness keeps that panel separate from Ragas and operational
  metrics.
- **Faithfulness coverage varies:** the local evaluator occasionally returned a
  null faithfulness score. Those rows remain `partial` with
  `score_missing_or_null`, are excluded from the mean, and appear in each
  ranking's evaluated/total coverage instead of becoming zero.
- **Cache effects:** n8n and graph-rag include cache hits in some cells.
- **Agentic cap:** `MAX_STEPS=4` materially limits `agentic-rag`.
- **Profile sensitivity:** fast, wide, and rerank profiles trade judge quality,
  answer relevancy, and latency differently by dataset; none is a universal
  replacement for the canonical profile.

## 10. Reversibility

- `qwen3.6-moe` was a historical LiteLLM runtime alias used during the early live
  run before the Atlas submodule gained first-class host-Ollama support.
- The recorded run used a local `models.yaml` compatibility layer for
  `think:false`; the current baseline removed that layer because Atlas's
  `qwen3.6:latest` catalog entry owns the same scoped request default.
- LightRAG role/query settings are Atlas inputs supplied by the parent-owned
  `config/atlas.env.user` imported by `atlas.consumer.yml`. Use an alternate
  `ATLAS_CONSUMER_MANIFEST` and env-file pair to experiment without editing the
  Atlas submodule.
