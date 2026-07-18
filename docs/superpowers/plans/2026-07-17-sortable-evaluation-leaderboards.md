# 7.8 Sortable Evaluation Leaderboards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish complete, deterministic, coverage-aware evaluation leaderboards whose individual metric columns are sortable on the `.io` site and remain complete static tables in repository Markdown and the GitHub Wiki.

**Architecture:** A focused Python aggregation module loads the active evaluation and judgment snapshots named by `compare/datasets.yaml`, validates them, and computes transparent base/flavor summaries. A separate renderer emits one canonical documentation page containing static HTML tables with machine-readable sort metadata. The existing three-surface pipeline copies a dependency-free local JavaScript module that progressively adds sorting and filters only on the `.io` site.

**Tech Stack:** Python 3.10+, JSON/YAML, pytest, dependency-free browser JavaScript, Node's built-in test runner, MkDocs Material, existing three-surface docs generator.

## Global Constraints

- Do not rerun the live stack or change the committed 2026-07-17 result artifacts.
- Never combine judge quality, Ragas metrics, latency, or reliability into a composite score.
- Rank base approaches and flavor aliases in separate tiers.
- Use dataset-macro judge mean for the default overall rank and expose query-weighted judge mean separately.
- Preserve ties with competition ranking; display missing or ineligible metrics as `N/A`, never zero.
- Keep metric values, coverage, evaluator failures, response failures, and timeouts in separate columns.
- JavaScript may sort/filter rendered rows but must not calculate scores, ranks, or fetch result data.
- Repository Markdown and Wiki output must remain complete without JavaScript.
- All three documentation surfaces must derive from canonical committed sources.
- Add no external JavaScript package, CDN, hosted service, or runtime dependency.

---

## File Map

| File | Responsibility |
|---|---|
| `compare/leaderboards.py` | Validate active snapshots and calculate cross-dataset and per-dataset leaderboard records. |
| `compare/report_leaderboards.py` | Render deterministic canonical Markdown/HTML tables and expose `--stdout` / `--output`. |
| `tests/test_evaluation_leaderboards.py` | Unit tests for aggregation, ties, coverage, validation, and report freshness. |
| `docs/evaluation-results.md` | Generated canonical leaderboard page committed for every surface. |
| `docs/javascripts/sortable-tables.js` | Dependency-free progressive sorting/filtering behavior for `.io`. |
| `tests/docs/test_sortable_tables.cjs` | Node tests for stable sorting, missing values, filtering, and reset order. |
| `tests/docs/test_three_surface_docs.py` | Site asset/config projection checks. |
| `scripts/docs/build_docs.py` | Copy local JavaScript to site input and register it in generated MkDocs config. |
| `docs/stylesheets/extra.css` | Table controls, sort state, focus, and narrow-screen overflow styling. |
| `docs/manifest.yaml` | Add the leaderboard page and renumber the Evaluation section consistently. |
| `README.md`, `docs/index.md`, `docs/comparison.md`, `docs/evaluation-methodology.md` | Point readers to the canonical full leaderboard and remove winner-only ambiguity. |

---

### Task 1: Deterministic Leaderboard Aggregation

**Files:**
- Create: `compare/leaderboards.py`
- Create: `tests/test_evaluation_leaderboards.py`

**Interfaces:**
- Consumes: parsed dataset rows from `compare/datasets.yaml`; evaluation dictionaries matching `compare.evaluation_summary.build_summary`; judgment dictionaries produced by `compare/judge.py`; flavor rows from `compare/flavors.yaml`.
- Produces: `build_leaderboards(datasets: list[dict[str, Any]], *, root: Path = ROOT) -> dict[str, Any]` with `base` and `flavors` tiers; each tier contains `overall`, `by_dataset`, `judge_models`, and `dataset_count`.
- Produces: `competition_ranks(values: dict[str, float | None], *, higher_is_better: bool) -> dict[str, int | None]`.
- Produces: `mean_pairwise_disagreement(scores: list[list[float]]) -> float | None`.

- [ ] **Step 1: Write failing aggregation tests with synthetic snapshots**

Create fixtures entirely under `tmp_path` so tests do not depend on current score values. Cover equal dataset weighting, query weighting, ties, per-model means, pairwise disagreement, Ragas weighted means and counters, latency weighted by successful rows, response totals, winner counts, and base/flavor separation.

```python
def test_overall_rank_uses_dataset_macro_mean(tmp_path: Path) -> None:
    datasets = _write_two_dataset_fixture(tmp_path)

    result = build_leaderboards(datasets, root=tmp_path)
    rows = {row["approach"]: row for row in result["base"]["overall"]}

    assert rows["approach-a"]["judge_macro_mean"] == 3.5
    assert rows["approach-a"]["judge_weighted_mean"] == 4.25
    assert rows["approach-b"]["judge_macro_mean"] == 3.0
    assert rows["approach-a"]["overall_rank"] == 1
    assert rows["approach-a"]["judge_evaluated"] == 4
    assert rows["approach-a"]["judge_total"] == 4


def test_missing_faithfulness_is_not_coerced_to_zero(tmp_path: Path) -> None:
    datasets = _write_graph_ineligible_fixture(tmp_path)
    row = build_leaderboards(datasets, root=tmp_path)["base"]["overall"][0]

    assert row["faithfulness_mean"] is None
    assert row["faithfulness_evaluated"] == 0
    assert row["faithfulness_not_evaluable"] == 2


def test_competition_ranks_preserve_ties() -> None:
    assert competition_ranks(
        {"a": 4.0, "b": 4.0, "c": 3.0}, higher_is_better=True
    ) == {"a": 1, "b": 1, "c": 3}
```

- [ ] **Step 2: Run the focused tests and confirm the missing module failure**

Run: `uv run pytest tests/test_evaluation_leaderboards.py -q`

Expected: collection fails with `ModuleNotFoundError: No module named 'compare.leaderboards'`.

- [ ] **Step 3: Implement snapshot validation and rank helpers**

Define explicit helpers; do not silently skip malformed measured snapshots.

```python
def competition_ranks(
    values: dict[str, float | None], *, higher_is_better: bool
) -> dict[str, int | None]:
    ranked = [(name, value) for name, value in values.items() if value is not None]
    ranked.sort(key=lambda item: ((-item[1] if higher_is_better else item[1]), item[0]))
    result = {name: None for name in values}
    previous: float | None = None
    previous_rank = 0
    for index, (name, value) in enumerate(ranked, start=1):
        rank = previous_rank if previous is not None and value == previous else index
        result[name] = rank
        previous = value
        previous_rank = rank
    return result


def mean_pairwise_disagreement(scores: list[list[float]]) -> float | None:
    differences: list[float] = []
    for query_scores in scores:
        for left in range(len(query_scores)):
            for right in range(left + 1, len(query_scores)):
                differences.append(abs(query_scores[left] - query_scores[right]))
    return round(sum(differences) / len(differences), 6) if differences else None
```

Validation must assert that each measured manifest row has the relevant evaluation and judgment paths, the evaluation contains exactly that dataset id, every judgment query has `mean_by_approach`, and evaluation/judgment approach sets match within a tier.

- [ ] **Step 4: Implement per-dataset records**

For every approach, flatten the evaluation summary without dropping counters. Add ranks by expanding the summary's tie groups and derive per-judge means/disagreement from `per_judge`.

```python
record = {
    "dataset": dataset_id,
    "complexity": int(dataset["complexity_level"]),
    "approach": approach,
    "base_family": base_family,
    "maturity": "experimental" if approach == "lazy-graph-rag" else "canonical",
    "judge_rank": judge_ranks.get(approach),
    "judge_mean": summary["judge_panel"]["mean"],
    "judge_evaluated": summary["judge_panel"]["evaluated"],
    "judge_total": summary["judge_panel"]["total"],
    "judge_by_model": judge_by_model,
    "judge_disagreement": disagreement,
    "answer_relevancy": summary["ragas"]["answer_relevancy"],
    "faithfulness": summary["ragas"]["faithfulness"],
    "operational": summary["operational"],
    "query_wins": wins.get(approach, 0),
}
```

- [ ] **Step 5: Implement overall records**

Aggregate means by their documented denominators. Dataset-macro judge mean is the arithmetic mean of per-dataset means; query-weighted, Ragas, latency, coverage, and counters use evaluated/successful/attempted counts.

```python
def _weighted_mean(points: list[tuple[float | None, int]]) -> float | None:
    usable = [(value, weight) for value, weight in points if value is not None and weight > 0]
    total = sum(weight for _, weight in usable)
    return round(sum(value * weight for value, weight in usable) / total, 6) if total else None


macro = _mean([row["judge_mean"] for row in rows if row["judge_mean"] is not None])
weighted = _weighted_mean([
    (row["judge_mean"], row["judge_evaluated"]) for row in rows
])
```

Apply `competition_ranks` to macro judge means and add mean/best/worst dataset rank. Sort default rows by `(overall_rank is None, overall_rank, approach)`.

- [ ] **Step 6: Run focused tests**

Run: `uv run pytest tests/test_evaluation_leaderboards.py -q`

Expected: all aggregation tests pass.

- [ ] **Step 7: Run Ruff and commit**

```bash
uv run ruff check compare/leaderboards.py tests/test_evaluation_leaderboards.py
git add compare/leaderboards.py tests/test_evaluation_leaderboards.py
git commit -m "feat: aggregate evaluation leaderboards"
```

---

### Task 2: Canonical Leaderboard Report

**Files:**
- Create: `compare/report_leaderboards.py`
- Create: `docs/evaluation-results.md`
- Modify: `tests/test_evaluation_leaderboards.py`

**Interfaces:**
- Consumes: `build_leaderboards(...)` from Task 1 and `docs/manifest.yaml` for the H1.
- Produces: `build_report() -> str`, `render_table(table_id: str, columns: list[Column], rows: list[dict[str, Any]]) -> str`, CLI `--stdout` and `--output` matching `compare/report_datasets.py` semantics.
- Produces: raw HTML tables carrying `class="results-table"`, a stable `id`, `data-sort-type` on headers, `data-sort-value` on cells, and `data-filter-*` on detailed rows.

- [ ] **Step 1: Add failing renderer and freshness tests**

```python
def test_leaderboard_report_contains_all_result_views() -> None:
    report = report_leaderboards.build_report()
    assert "## 2. Overall Base-Approach Leaderboard" in report
    assert 'id="base-overall"' in report
    assert 'id="base-by-dataset"' in report
    assert 'id="flavor-overall"' in report
    assert 'id="flavor-by-dataset"' in report
    assert "Dataset-macro judge" in report
    assert "Query-weighted judge" in report
    assert "Faithfulness coverage" in report
    assert "Errors" in report
    assert "Timeouts" in report


def test_committed_leaderboard_report_is_fresh() -> None:
    assert report_leaderboards.build_report() == (
        ROOT / "docs" / "evaluation-results.md"
    ).read_text(encoding="utf-8")
```

- [ ] **Step 2: Confirm the renderer test fails**

Run: `uv run pytest tests/test_evaluation_leaderboards.py -q`

Expected: import or assertion failure because the report module/page does not exist.

- [ ] **Step 3: Implement deterministic formatting primitives**

Use an immutable column definition and keep machine values distinct from display values.

```python
@dataclass(frozen=True)
class Column:
    key: str
    label: str
    sort_type: Literal["number", "text"] = "number"
    direction: Literal["higher", "lower", "neutral"] = "higher"


def _cell(value: Any, display: str) -> str:
    sort_value = "" if value is None else str(value)
    return f'<td data-sort-value="{html.escape(sort_value)}">{html.escape(display)}</td>'


def _number(value: float | None, digits: int = 2) -> str:
    return "N/A" if value is None else f"{value:.{digits}f}"
```

The table renderer emits a caption, accessible header scope, row filter metadata,
and complete static cells. Do not render sort buttons; the site script adds them.

- [ ] **Step 4: Implement the four tables and derived interpretation**

Render:

1. overall base approaches;
2. base approach by dataset;
3. overall flavor aliases;
4. flavor alias by dataset.

Include all fields defined by the design. Dynamically add one column per recorded
judge model, ordered by model name. Add clear prose explaining metric direction,
coverage, macro versus weighted means, faithfulness ineligibility, and why base and
flavor tiers are separate. Link to methodology, narrative comparison, dataset
ladder, and raw result snapshots.

- [ ] **Step 5: Implement CLI behavior and generate the committed page**

```python
if args.stdout:
    sys.stdout.write(report)
else:
    output = args.output or DEFAULT_OUTPUT
    output.write_text(report, encoding="utf-8")
    print(f"wrote {_display_path(output)}")
```

Run:

```bash
uv run python compare/report_leaderboards.py --output docs/evaluation-results.md
uv run python compare/report_leaderboards.py --stdout > /tmp/rag-showcase-leaderboards.md
diff -u docs/evaluation-results.md /tmp/rag-showcase-leaderboards.md
```

Expected: the generator reports the output path and `diff` emits no output.

- [ ] **Step 6: Run focused tests and commit**

```bash
uv run pytest tests/test_evaluation_leaderboards.py -q
uv run ruff check compare/report_leaderboards.py tests/test_evaluation_leaderboards.py
git add compare/report_leaderboards.py tests/test_evaluation_leaderboards.py docs/evaluation-results.md
git commit -m "docs: generate complete evaluation leaderboards"
```

---

### Task 3: Dependency-Free Sorting and Filtering

**Files:**
- Create: `docs/javascripts/sortable-tables.js`
- Create: `tests/docs/test_sortable_tables.cjs`
- Modify: `docs/stylesheets/extra.css`
- Modify: `scripts/docs/build_docs.py`
- Modify: `tests/docs/test_three_surface_docs.py`

**Interfaces:**
- Consumes: Task 2 table classes and `data-sort-*` / `data-filter-*` attributes.
- Produces: CommonJS-testable helpers `compareValues`, `stableSort`, and `matchesFilters`; browser initializer `enhanceTable(table)`.
- Produces: generated-site asset `generated/site/javascripts/sortable-tables.js` and `extra_javascript: [javascripts/sortable-tables.js]` in generated `mkdocs.yml`.

- [ ] **Step 1: Write failing pure-behavior Node tests**

```javascript
const test = require("node:test");
const assert = require("node:assert/strict");
const tables = require("../../docs/javascripts/sortable-tables.js");

test("missing values sort after numeric values in both directions", () => {
  const rows = [{ value: null, index: 0 }, { value: 2, index: 1 }, { value: 5, index: 2 }];
  assert.deepEqual(tables.stableSort(rows, "value", "number", "asc").map(r => r.value), [2, 5, null]);
  assert.deepEqual(tables.stableSort(rows, "value", "number", "desc").map(r => r.value), [5, 2, null]);
});

test("filters combine dataset and approach", () => {
  assert.equal(tables.matchesFilters(
    { dataset: "graph_native", approach: "graph-rag" },
    { dataset: "graph_native", approach: "graph-rag" }
  ), true);
  assert.equal(tables.matchesFilters(
    { dataset: "baseline_curated", approach: "graph-rag" },
    { dataset: "graph_native", approach: "graph-rag" }
  ), false);
});
```

- [ ] **Step 2: Confirm the Node tests fail**

Run: `node --test tests/docs/test_sortable_tables.cjs`

Expected: failure because `docs/javascripts/sortable-tables.js` does not exist.

- [ ] **Step 3: Implement pure sort/filter helpers**

```javascript
function compareValues(left, right, type, direction) {
  const leftMissing = left === null || left === undefined || left === "";
  const rightMissing = right === null || right === undefined || right === "";
  if (leftMissing || rightMissing) {
    if (leftMissing && rightMissing) return 0;
    return leftMissing ? 1 : -1;
  }
  const a = type === "number" ? Number(left) : String(left).toLocaleLowerCase();
  const b = type === "number" ? Number(right) : String(right).toLocaleLowerCase();
  const result = a < b ? -1 : a > b ? 1 : 0;
  return direction === "desc" ? -result : result;
}

function stableSort(records, key, type, direction) {
  return [...records].sort((a, b) =>
    compareValues(a[key], b[key], type, direction) || a.index - b.index
  );
}

function matchesFilters(values, filters) {
  return Object.entries(filters).every(([key, expected]) =>
    !expected || values[key] === expected
  );
}
```

Export helpers under CommonJS when available and initialize only when `document`
exists, so the same dependency-free file is testable by Node and usable directly
by MkDocs.

- [ ] **Step 4: Implement accessible DOM enhancement**

For every `.results-table`, wrap each header label in a real `<button type="button">`,
set `aria-sort` on the active `<th>`, preserve original row indexes, and cycle
ascending/descending on click. Dynamically add dataset/approach `<select>` controls
and a reset `<button>` only to tables carrying `data-filterable="true"`. Reset
clears filters, restores original row order, and clears `aria-sort`.

- [ ] **Step 5: Add styles and three-surface site registration tests**

Extend the docs test:

```python
def test_sortable_table_script_is_site_only_and_registered(tmp_path: Path) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"
    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)

    assert (site_dir / "javascripts" / "sortable-tables.js").is_file()
    assert not (wiki_dir / "javascripts" / "sortable-tables.js").exists()

    config = tmp_path / "mkdocs.yml"
    render_mkdocs_yml(manifest, config)
    assert "javascripts/sortable-tables.js" in config.read_text(encoding="utf-8")
```

Modify `render_site` to copy `docs/javascripts`, and add
`"extra_javascript": ["javascripts/sortable-tables.js"]` beside `extra_css`.
CSS must provide visible keyboard focus, compact controls, sort direction markers,
sticky first columns where practical, and horizontal overflow without overlapping
headers or values.

- [ ] **Step 6: Run behavior and docs-pipeline tests**

```bash
node --test tests/docs/test_sortable_tables.cjs
uv run pytest tests/docs/test_three_surface_docs.py -q
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add docs/javascripts/sortable-tables.js docs/stylesheets/extra.css \
  scripts/docs/build_docs.py tests/docs/test_sortable_tables.cjs \
  tests/docs/test_three_surface_docs.py
git commit -m "feat: add sortable documentation tables"
```

---

### Task 4: Promote the Leaderboards Across All Documentation Surfaces

**Files:**
- Modify: `docs/manifest.yaml`
- Modify: `README.md`
- Modify: `docs/index.md`
- Modify: `docs/comparison.md`
- Modify: `docs/evaluation-methodology.md`
- Modify: `docs/dataset-complexity-report.md` via its generator
- Modify: `compare/report_datasets.py`
- Modify: `docs/results/README.md`
- Modify: `tests/test_dataset_report.py`
- Modify: `tests/test_approach_docs.py`

**Interfaces:**
- Consumes: canonical `docs/evaluation-results.md` from Task 2.
- Produces: Evaluation nav order `5.1 Methodology`, `5.2 Evaluation Results and Leaderboards`, `5.3 Live Comparison`, `5.4 Dataset Complexity Report`, `5.5 Live Run Result Snapshots`.

- [ ] **Step 1: Add failing navigation and cross-link assertions**

Update documentation tests to require:

```python
assert "evaluation-results.md" in manifest_sources
assert "[Full sortable leaderboards](evaluation-results.md)" in index
assert "docs/evaluation-results.md" in readme
assert "[complete leaderboards](evaluation-results.md)" in comparison
```

Require the generated dataset report H1 to follow its new manifest number.

- [ ] **Step 2: Confirm focused documentation tests fail**

Run:

```bash
uv run pytest tests/test_dataset_report.py tests/test_approach_docs.py tests/docs/test_three_surface_docs.py -q
```

Expected: assertions fail until navigation, headings, and links are updated.

- [ ] **Step 3: Update the manifest and numbered headings**

Insert the new page as 5.2 and renumber the existing evaluation pages to 5.3,
5.4, and 5.5. Update canonical H1s and let `report_datasets.py` derive `# 5.4`
from the manifest. Keep the design and implementation plan as 7.7 and 7.8.

- [ ] **Step 4: Replace winner-only navigation with a canonical leaderboard path**

Keep the concise winner table on the home page and README, but state that it is a
headline, link directly to `evaluation-results.md`, and say that the full page
contains every approach/metric rather than only winners. In `comparison.md`,
replace the winner-only “Current Seven-Approach Results” table with a compact
interpretive summary plus a direct link to the complete base and flavor tables.
Do not duplicate generated metrics manually.

- [ ] **Step 5: Clarify methodology and dataset-report roles**

`evaluation-methodology.md` points to the new page as the canonical presentation
layer. `dataset-complexity-report.md` remains the generated ladder/per-query view
and links back to the sortable leaderboards. `docs/results/README.md` remains the
artifact ledger. Each page must have one distinct responsibility.

- [ ] **Step 6: Regenerate reports and all documentation projections**

```bash
uv run python compare/report_leaderboards.py --output docs/evaluation-results.md
uv run python compare/report_datasets.py --output docs/dataset-complexity-report.md
uv run python -m scripts.docs.build_docs
make docs-check
```

Expected: strict MkDocs build succeeds; generated site and Wiki contain the full
static table text; the generated site additionally contains the local script.

- [ ] **Step 7: Run focused tests, inspect diff, and commit**

```bash
uv run pytest tests/test_dataset_report.py tests/test_approach_docs.py \
  tests/test_evaluation_leaderboards.py tests/docs/test_three_surface_docs.py -q
git diff --check
git add README.md compare/report_datasets.py docs tests/test_dataset_report.py \
  tests/test_approach_docs.py
git commit -m "docs: publish comprehensive evaluation rankings"
```

---

### Task 5: Full Verification, Visual Validation, and GitFlow Promotion

**Files:**
- Modify only if verification exposes a defect in files already in scope.

**Interfaces:**
- Consumes: completed feature branch.
- Produces: verified feature PR into `develop`, promotion PR from `develop` into `main`, published three-surface docs, and branch/worktree cleanup.

- [ ] **Step 1: Run all automated verification**

```bash
node --test tests/docs/test_sortable_tables.cjs
uv run ruff check compare/leaderboards.py compare/report_leaderboards.py \
  tests/test_evaluation_leaderboards.py scripts/docs/build_docs.py
uv run pytest tests backend_plugins/rag/tests -q
make docs-check
git diff --check
```

Expected: Node tests pass; Ruff reports no errors; pytest passes with only declared
environment-dependent skips; docs build is strict and deterministic; diff check is clean.

- [ ] **Step 2: Inspect all three generated surfaces**

Assert the same approach names and key metrics appear in canonical, site, and Wiki
projections:

```bash
for file in docs/evaluation-results.md \
  generated/site/evaluation-results.md \
  generated/wiki/5.2-Evaluation-Results-and-Leaderboards.md; do
  rg -q 'vanilla-rag' "$file"
  rg -q 'lazy-graph-rag' "$file"
  rg -q 'Dataset-macro judge' "$file"
done
```

- [ ] **Step 3: Run local browser verification**

Start MkDocs on an unused localhost port, open
`evaluation-results.html`, and verify desktop plus mobile-width behavior:

- every table renders nonblank with no overlapping headers/cells;
- sorting judge, Ragas, latency, coverage, error, and text columns changes order;
- missing faithfulness remains last in both directions;
- dataset/approach filters combine correctly;
- reset restores canonical order;
- controls are keyboard operable and `aria-sort` changes;
- horizontal overflow works on narrow screens.

Capture a screenshot for review, then keep the final server URL available until
the integration work completes.

- [ ] **Step 4: Request independent code review and address findings**

Review aggregation arithmetic, artifact validation, static fallback, script
accessibility, report freshness, and three-surface projection. Fix verified findings
with focused tests and rerun Step 1.

- [ ] **Step 5: Push and merge the feature PR into `develop`**

```bash
git push
gh pr create --base develop --head codex/sortable-evaluation-leaderboards \
  --title "docs: add sortable evaluation leaderboards" \
  --body-file /tmp/rag-showcase-leaderboards-pr.md
gh pr checks <feature-pr-number> --watch
gh pr merge <feature-pr-number> --merge --delete-branch
```

Expected: required checks pass and the feature PR merges into `develop`.

- [ ] **Step 6: Promote `develop` into `main` through a second PR**

```bash
gh pr create --base main --head develop \
  --title "release: promote sortable evaluation leaderboards" \
  --body-file /tmp/rag-showcase-leaderboards-promotion.md
gh pr checks <promotion-pr-number> --watch
gh pr merge <promotion-pr-number> --merge
```

Expected: promotion checks pass and `main` receives the same tree as `develop`.

- [ ] **Step 7: Verify publication and clean repository state**

Fetch/prune, compare `main` and `develop` tree hashes, delete merged feature
branches locally/remotely, remove non-primary worktrees, close only superseded
open PRs after confirming merge state, and verify the `.io` page and Wiki page
return HTTP 200 with the new leaderboard content. Final state must contain only
local/remote `main` and `develop` branches and the required primary worktree.

