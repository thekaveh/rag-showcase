# Approach Lifecycle Comparison and Renewed Evaluation Design

## 1. Goal

Publish a durable, metrics-free comparison of every implemented and researched
RAG approach family, then perform a fresh evaluation of only the approaches that
rag-showcase actually deploys. The documentation must make that boundary
unambiguous: researched candidates can be compared architecturally without being
assigned fabricated scores.

## 2. Documentation Structure

The canonical lifecycle comparison belongs in `docs/approaches.md`, after the
shared invocation and evaluation contracts and before current measured results.
Readers should understand what is deployed, when knowledge is prepared, and how
state changes before interpreting rankings.

The section will contain two companion tables rather than one unreadable table
with more than a dozen columns:

1. **Knowledge lifecycle and persistence** compares status, current employment,
   knowledge preparation, chunk enrichment, graph timing, graph orientation,
   durable state, and whether query-derived learning persists.
2. **Query execution and evidence** compares routing or tool selection,
   retrieval, reranking, generation ownership, ingest/query model work, exposed
   evidence, principal tuning knobs, best-fit questions, and characteristic
   failure modes.

Both tables cover these nine approach families:

- `vanilla-rag`
- `hybrid-rag`
- `contextual-rag`
- `graph-rag` (Atlas LightRAG)
- `agentic-rag`
- `n8n-adaptive-rag`
- `lazy-graph-rag`
- proposed `graphify-rag`
- proposed `llm-wiki-rag`

The lifecycle table will include a dedicated **Employed in showcase?** column:

- **Yes** for the six canonical deployed approaches.
- **Experimental** for deployed but opt-in `lazy-graph-rag`.
- **No - TBD** for researched, unimplemented Graphify RAG and LLM Wiki RAG.

This column is independent from the maturity/status column. For example,
`lazy-graph-rag` is employed but experimental, while Graphify RAG is a researched
candidate and not employed.

Approach flavors remain tuning variants of their family rather than separate
rows. Their parameter differences continue to live in
`docs/approach-flavor-tuning.md` and in the empirical flavor results.

## 3. Factual Comparison Contract

Every lifecycle statement must be supported by the deployed implementation,
Atlas integration contract, or cited primary source for a candidate:

- LightRAG constructs its entity/relationship graph during ingestion and reuses
  it at query time.
- Agentic RAG selects tools during its bounded ReAct loop but does not persist
  its trajectory or learn between queries.
- Lazy Graph RAG constructs its deterministic concept graph on the first query
  after a cache miss, persists it by corpus fingerprint, and does not mutate it
  from query feedback.
- n8n classifies once per query and delegates to another approach; it owns no
  retrieval index.
- Graphify is described as a prebuilt typed graph retriever that requires a
  showcase generation wrapper before it becomes an end-to-end RAG route.
- LLM Wiki is described as a persistent, human-readable knowledge-compilation
  pattern; query writeback is optional and would be disabled during benchmarks.

Candidate rows must say **unimplemented and unmeasured** and must not appear in
rankings, means, progression charts, or success-rate denominators.

## 4. Renewed Evaluation Scope

The final empirical comparison covers the current implemented showcase only:

- Seven base approach routes over the 20 queries in the three measured dataset
  rungs: 140 fresh answer cells.
- Eleven declared flavor aliases over the same queries as a separate tuning
  tier: 220 fresh answer cells.
- 360 fresh answer cells overall.

Base-family rankings and flavor rankings remain separate. A flavor cannot occupy
multiple places in the base-family leaderboard, and experimental lazy graph is
visibly labeled in every aggregate.

The three measured rungs are `baseline_curated`, `graph_native`, and
`cyber_threat_intel`. Candidate datasets remain outside this renewed run unless
they are separately materialized, validated, and promoted to measured status.

## 5. Evaluation Preconditions

Before collecting answers:

1. Update the Atlas submodule to a current `main` commit containing the resolved
   evaluator fixes for Ragas metric construction and contextless rows.
2. Reconcile rag-showcase consumer configuration with the selected Atlas commit.
3. Configure evaluator and embedding roles explicitly without encoding a
   particular hardware assumption.
4. Correct evidence contracts. The current n8n workflow shapes its delegated
   response down to `answer`, `route`, and `approach`, while the plugin emits only
   an adaptive-route marker as a source. It must preserve downstream structured
   contexts and metrics or be declared `answer_only`; a route label must never be
   evaluated as grounding context.
5. Pass repository tests, documentation checks, Atlas consumer validation,
   evaluator smoke tests, and a live smoke across all seven base routes.

## 6. Fresh-Run Procedure

For each measured dataset:

1. Start the current Atlas-backed stack and capture exact repository, submodule,
   manifest, model-role, and dataset revisions.
2. Reset dataset-scoped retrieval state and submit a fresh Atlas ingestion.
3. Wait for parser, chunk, embedding, Weaviate, and LightRAG extraction phases to
   complete successfully.
4. Rebuild the contextual collection from that ingestion's chunks.
5. Clear the lazy-graph cache so first-build time and state belong to this run.
6. Execute the seven base routes with cache-bypass controls.
7. Execute the eleven flavor aliases as a distinct tuning matrix.
8. Persist normalized answers, contexts, approach metadata, errors, latency,
   chunk counts, model-call counts, ingestion provenance, and configuration
   hashes before evaluation.
9. Run Atlas-backed Ragas metrics according to evidence eligibility and run the
   two-model blinded judge panel over stored answers.
10. Tear down the stack after all artifacts and service logs needed for audit are
    preserved.

Interrupted evaluations resume from canonical rows only when their run identity,
configuration hashes, and ingestion provenance match. Answers are not regenerated
merely because an evaluator call needs retrying.

## 7. Result Outputs

Generated documentation will report:

- successful-answer and error rates;
- latency distribution, not only arithmetic mean;
- answer relevancy coverage and score;
- faithfulness coverage and score only where real contexts exist;
- two-judge means and disagreement;
- per-dataset base rankings;
- rank and score progression across the dataset ladder;
- base-versus-flavor effects without mixing the leaderboards;
- ingestion and query costs where the services expose them;
- explicit `not_evaluable` and error states rather than coerced zeroes;
- reproducibility metadata and links to canonical result artifacts.

Graphify RAG and LLM Wiki RAG appear only in the architectural comparison until
separate implementation and evaluation work is approved and completed.

## 8. Documentation Surfaces

Canonical Markdown remains the source. The implementation will update the
documentation manifest where required, regenerate the MkDocs and wiki surfaces,
and run `make docs-check`. Generated surfaces must not introduce independent
wording or hand-maintained copies of the lifecycle tables.

## 9. Acceptance Criteria

- `docs/approaches.md` contains the dedicated two-table lifecycle section in the
  agreed location.
- All nine families appear, with a separate **Employed in showcase?** column.
- Candidate approaches are clearly unimplemented and unmeasured.
- No candidate receives a score, rank, or implied test result.
- The n8n evidence capability matches the evidence it actually returns.
- The latest compatible Atlas evaluator fixes are pinned and validated.
- All 140 base and 220 flavor cells have explicit success or error records.
- Ragas and judge coverage are reported independently and honestly.
- Fresh per-dataset, progression, and flavor reports are generated from canonical
  artifacts.
- Tests and `make docs-check` pass before pull requests are promoted through
  feature to `develop`, then `develop` to `main`.
