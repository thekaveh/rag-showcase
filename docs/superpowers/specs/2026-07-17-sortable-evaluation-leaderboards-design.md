# 7.7 Sortable Evaluation Leaderboards Design

**Date:** 2026-07-17
**Status:** Approved for implementation
**Audience:** rag-showcase users, evaluators, and maintainers

## 1. Objective

Make the current evaluation results comprehensible from the main documentation.
The repository already stores complete, coverage-aware metrics, but the headline
pages show only dataset winners while the generated dataset report compresses
complete rankings into long text strings. Readers cannot compare every approach,
sort by a metric they care about, or distinguish an unavailable score from a
poor score without inspecting JSON artifacts.

The result documentation will provide one canonical, reproducible leaderboard
view generated from the committed evaluation and judgment snapshots. It will
publish to all three documentation surfaces:

- repository Markdown rendered by GitHub;
- the generated GitHub Wiki;
- the generated MkDocs `.io` site.

The `.io` site will progressively enhance the same tables with client-side
sorting and filtering. Repository Markdown and the Wiki will retain complete,
useful static tables in the default ranking order.

## 2. Ranking Contract

No composite score will combine judge quality, Ragas metrics, latency, or
reliability. Each metric remains an independent column and can be ranked on its
own.

The default overall base-family ordering is the macro-average judge score: each
measured dataset contributes equally, regardless of its query count. This makes
the progression over dataset complexity visible without allowing the eight-query
graph-native rung to outweigh the six-query baseline and cyber rungs. The table
will also expose the query-weighted judge mean as a separate column so readers can
inspect the alternate aggregation directly.

Ties use competition ranking and remain ties. Missing and ineligible metrics sort
after numeric values and display as `N/A`, never as zero. Coverage appears in
separate sortable columns next to every metric whose evaluation can be partial.
Lower latency and lower failure counts are better; higher quality, coverage, and
success values are better. Column labels and nearby prose state these directions.

Base approaches and flavor aliases remain separate leaderboards. A tuned flavor
cannot occupy a position in the base-family ranking.

## 3. Canonical Data Flow

The committed artifacts under `docs/results/` remain the source evidence. The
dataset manifest identifies the active snapshots for each measured rung. A
deterministic report generator will:

1. load each measured dataset's base and flavor evaluation JSON;
2. load the corresponding judgment JSON for per-query wins and query-weighted
   judge values;
3. validate that datasets, approaches, query counts, and coverage agree;
4. calculate only transparent cross-dataset aggregates;
5. emit the canonical Markdown tables into the main comparison document or a
   generated results document referenced by it;
6. emit stable table metadata used only for `.io` progressive enhancement.

No browser code will calculate scores or ranks. JavaScript may reorder or filter
already rendered rows, but the Python generator owns every displayed value and
default rank. This keeps the repository and Wiki output authoritative even when
JavaScript is unavailable.

## 4. Result Views

### 4.1 Executive Summary

The documentation home page and root README will retain a compact result summary:

- run date and evaluation scope;
- base winner for each measured dataset;
- link to the full leaderboard;
- explicit statement that winners vary by dataset and metric.

These pages will not duplicate the complete tables. The canonical comparison page
is the reader-facing source for detailed results.

### 4.2 Overall Base-Approach Leaderboard

One row per implemented base approach, including experimental
`lazy-graph-rag`, with these independent fields:

| Field | Meaning |
|---|---|
| Overall judge rank | Competition rank by dataset-macro judge mean. |
| Approach | OpenAI-compatible model alias. |
| Maturity | Canonical or experimental. |
| Dataset-macro judge mean | Equal-weight mean of the per-dataset judge means. |
| Query-weighted judge mean | Mean over all evaluated queries. |
| Per-judge means | One column per recorded judge model. |
| Judge disagreement | Mean absolute score difference between panel members. |
| Judge coverage | Evaluated judge questions / eligible questions. |
| Mean dataset rank | Mean of the approach's rank on each measured dataset. |
| Best / worst dataset rank | Range showing rank stability. |
| Per-query wins | Queries where the judgment artifact names the approach winner. |
| Answer relevancy mean | Query-weighted Ragas answer-relevancy mean. |
| Answer relevancy coverage | Evaluated / eligible rows. |
| Answer relevancy evaluator failures | Evaluator errors and timeouts, kept separate. |
| Faithfulness mean | Mean over evaluated, eligible faithfulness rows only. |
| Faithfulness coverage | Evaluated / eligible rows, with ineligible rows visible. |
| Faithfulness evaluator status | Not-evaluable rows, evaluator errors, and evaluator timeouts. |
| Mean latency | Query-weighted mean successful-response latency. |
| Successful / attempted | Operational response coverage. |
| Error rate | Errors and timeouts divided by attempted responses. |
| Errors | Response error count. |
| Timeouts | Response timeout count. |

The default order uses overall judge rank. Every numeric column is independently
sortable on the `.io` surface.

### 4.3 Dataset-by-Approach Leaderboard

One row per measured dataset and base approach exposes progression without dense
ranking strings. Columns include dataset, complexity, approach, per-dataset judge
rank and mean, judge coverage, answer-relevancy rank/mean/coverage,
faithfulness rank/mean/coverage/ineligible/error/timeout counts, per-judge means,
judge disagreement, latency rank/mean, successful, attempted, error rate, errors,
and timeouts.

The `.io` surface provides dataset and approach filters plus sortable columns.
Static surfaces order rows by dataset complexity, then judge rank. Candidate
datasets remain listed in the dataset ladder but do not receive fabricated rows
or rankings.

### 4.4 Flavor Leaderboards

Flavor results use the same metric columns in a separate section. The overall
flavor table compares only named non-base aliases. A detailed flavor-by-dataset
table follows it. Each row identifies its base family so readers can compare a
flavor with the corresponding default without mixing tiers.

### 4.5 Per-Query Detail

The existing per-query winner view remains available as supporting detail. It is
not the primary leaderboard because one winning vote does not expose the complete
quality, coverage, or latency tradeoff. The detailed view links to the stored
judgment artifacts for per-judge scores and reasons.

## 5. Interactive Behavior

Sortable tables use progressive enhancement and no external JavaScript service or
runtime dependency. The generated site copies a small local script and registers
it through the generated MkDocs configuration.

- Header buttons expose ascending/descending state through `aria-sort`.
- Numeric columns sort by machine-readable values rather than formatted text.
- Text columns sort case-insensitively.
- Missing values always follow real values in either direction.
- The active sort column and direction remain visually apparent.
- Dataset and approach filters operate only on the detailed tables.
- A reset control restores the generator's canonical row order.
- Keyboard activation and focus styling match pointer behavior.
- Tables remain horizontally scrollable on narrow viewports.

The script must not alter cell contents, calculate aggregate values, fetch remote
data, or hide missing-coverage warnings.

## 6. Three-Surface Publication

Canonical Markdown and committed artifacts are edited once. The existing docs
pipeline projects them into the generated site and Wiki:

- GitHub repository: complete static tables in the default meaningful order;
- GitHub Wiki: the same complete static tables and local artifact links;
- `.io` site: identical table contents plus local sorting and filtering behavior.

The README and documentation home page receive concise, consistent summaries and
links to the canonical leaderboard. Generated trees remain gitignored and are
never hand-edited. `make docs-check` must prove deterministic projection and
self-contained links.

## 7. Validation and Failure Handling

Generation fails before changing the committed report when an active snapshot is
missing, malformed, references a different dataset, omits a configured approach,
or has incompatible query/coverage totals. A metric may be absent only when its
artifact explicitly marks it ineligible or unevaluated.

Tests cover:

- deterministic overall and per-dataset aggregates;
- equal dataset weighting for the primary judge score;
- separate query-weighted judge score;
- competition ranks and ties;
- missing/ineligible values and coverage rendering;
- strict separation of base and flavor tiers;
- complete column sets and stable table identifiers;
- sortable numeric, text, missing-value, reset, and filter behavior;
- static fallback contents;
- three-surface generation and strict MkDocs build.

## 8. Non-Goals

- Rerunning the live stack or changing the recorded 2026-07-17 metrics.
- Inventing a blended quality/cost score.
- Ranking unimplemented candidate approaches or unmeasured candidate datasets.
- Replacing the committed JSON/JSONL artifacts with a database or hosted service.
- Building a standalone evaluation web application.

## 9. Acceptance Criteria

- The main comparison documentation contains a complete overall ranking of all
  seven measured base approaches.
- Every currently recorded quality, coverage, latency, and response-status metric
  appears in a separate column in an appropriate table.
- Base-family and flavor results remain separate.
- The dataset view exposes every measured approach on every measured dataset and
  makes performance progression easy to compare.
- The default rank uses dataset-macro judge mean; query-weighted judge mean is
  independently visible.
- The `.io` tables sort every column and filter detailed views without external
  dependencies or client-side score calculation.
- Repository Markdown and Wiki tables remain complete and understandable without
  JavaScript.
- README and documentation-home summaries link readers to the canonical full
  leaderboard.
- Generator, interaction, report-freshness, docs, and repository tests pass.
- The feature is promoted through a feature-to-`develop` PR and a subsequent
  `develop`-to-`main` PR, after which only local and remote `develop` and `main`
  branches and their required worktrees remain.
