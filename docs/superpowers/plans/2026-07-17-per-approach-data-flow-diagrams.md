# Per-Approach Service-Aware Data-Flow Diagrams Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish seven detailed, landscape, service-aware data-flow diagrams under the matching approach sections on repository Markdown, the generated MkDocs `.io` site, and the generated GitHub Wiki.

**Architecture:** Keep the existing full-system and parallel-lane diagrams as overviews. Add one standalone HTML/inline-SVG source and one 2x PNG per approach, combining service topology with numbered ingestion/query messages; keep `docs/approaches.md` canonical and recursively publish/rewrite nested assets for site and Wiki output.

**Tech Stack:** Standalone HTML, inline SVG, CSS, JetBrains Mono, headless Google Chrome, Python 3.11, pytest, MkDocs Material, GitHub Wiki generation, Git, GitHub CLI.

## Global Constraints

- Work only on `codex/per-approach-data-flow-diagrams`, based on current `develop`.
- Generate exactly seven diagrams: Vanilla, Hybrid, Contextual, Graph/LightRAG, Agentic, n8n Adaptive, and experimental Lazy Graph RAG.
- Use one combined architecture-and-data-flow diagram per approach, not two redundant images.
- Each HTML file is standalone with inline SVG/CSS, no JavaScript, an `1800 x 1000` landscape composition, and `viewBox="0 0 1800 900"`.
- Render each PNG from HTML at 2x scale, approximately `3600 x 2000`.
- Use orthogonal routing, opaque box backplates, arrows behind boxes, at least 40px gaps, and legends outside boundaries.
- No clipped text, overlaps, line-through-text routing, ambiguous direction, or dangling arrow heads/tails.
- Name actual services, stores, model roles, message payloads, response evidence, persistent state, and tuning points.
- Keep `docs/approaches.md` canonical. Do not hand-author site or Wiki copies.
- Preserve the existing overview diagrams and publish through feature-to-`develop` then `develop`-to-`main` PRs.

---

### Task 1: Add Recursive Three-Surface Diagram Publication

**Files:**
- Modify: `scripts/docs/build_docs.py`
- Modify: `scripts/docs/transforms.py`
- Modify: `tests/docs/test_three_surface_docs.py`

**Interfaces:**
- Consumes: `docs/diagrams/approaches/<approach>/data-flow.{html,png}` links.
- Produces: path-preserving site assets under `assets/diagrams/approaches/`, Wiki assets under `diagrams/approaches/`, and rewritten local links.

- [ ] **Step 1: Write the failing publication test**

```python
def test_generated_surfaces_publish_nested_approach_diagrams(tmp_path) -> None:
    manifest = load_manifest()
    pages = iter_pages(manifest)
    site_dir = tmp_path / "site"
    wiki_dir = tmp_path / "wiki"
    render_site(manifest, pages, site_dir)
    render_wiki(manifest, pages, wiki_dir)
    expected = {
        p.relative_to(DOCS / "diagrams" / "approaches")
        for p in (DOCS / "diagrams" / "approaches").rglob("*")
        if p.is_file() and p.suffix in {".html", ".png"}
    }
    assert expected
    for relative in expected:
        assert (site_dir / "assets/diagrams/approaches" / relative).is_file()
        assert (wiki_dir / "diagrams/approaches" / relative).is_file()
    check_local_links(site_dir)
    check_local_links(wiki_dir)
```

- [ ] **Step 2: Run it and verify RED**

Run `uv run pytest tests/docs/test_three_surface_docs.py::test_generated_surfaces_publish_nested_approach_diagrams -q`.

Expected: FAIL because nested assets are absent or unpublished.

- [ ] **Step 3: Copy nested assets recursively**

Add `_copy_tree_files(DOCS / "diagrams" / "approaches", site_dir / "assets" / "diagrams" / "approaches")` to `render_site()` and the equivalent Wiki target `wiki_dir / "diagrams" / "approaches"` to `render_wiki()`.

- [ ] **Step 4: Implement path-preserving link rewriting**

```python
def _nested_diagram_target(
    link_source: PurePosixPath, clean_target: str, surface: str
) -> str | None:
    if not clean_target.startswith("diagrams/approaches/"):
        return None
    relative = clean_target.removeprefix("diagrams/")
    destination = (
        f"diagrams/{relative}"
        if surface == "wiki"
        else f"assets/diagrams/{relative}"
    )
    return _relative(link_source, destination)
```

Invoke it before legacy flat handlers and retain `!` for images. Commit this task with Task 2 so the tree is never knowingly red.

### Task 2: Establish Contract and Create Vanilla/Hybrid Diagrams

**Files:**
- Create: `docs/diagrams/approaches/vanilla-rag/data-flow.{html,png}`
- Create: `docs/diagrams/approaches/hybrid-rag/data-flow.{html,png}`
- Modify: `docs/approaches.md`
- Modify: `tests/test_approach_docs.py`

**Interfaces:**
- Consumes: LiteLLM aliases, backend routes, `RagBase_<profile>`, TEI, `embed`, and `light_gen`.
- Produces: common diagram grammar and canonical embedding pattern.

- [ ] **Step 1: Write a failing parametrized seven-approach contract**

```python
@pytest.mark.parametrize("approach", [
    "vanilla-rag", "hybrid-rag", "contextual-rag", "graph-rag",
    "agentic-rag", "n8n-adaptive-rag", "lazy-graph-rag",
])
def test_approach_has_landscape_data_flow_diagram(approach) -> None:
    directory = ROOT / "docs/diagrams/approaches" / approach
    source = (directory / "data-flow.html").read_text(encoding="utf-8")
    assert (directory / "data-flow.png").is_file()
    assert approach in source
    assert 'viewBox="0 0 1800 900"' in source
    docs = (ROOT / "docs/approaches.md").read_text(encoding="utf-8")
    assert f"diagrams/approaches/{approach}/data-flow.png" in docs
    assert f"diagrams/approaches/{approach}/data-flow.html" in docs
```

- [ ] **Step 2: Run Vanilla/Hybrid cases and verify RED**

Run `uv run pytest tests/test_approach_docs.py -k 'landscape and (vanilla or hybrid)' -q`; expect two missing-asset failures.

- [ ] **Step 3: Build Vanilla RAG HTML/SVG**

Messages: `0.1` corpus/profile to Atlas ingestion; `0.2` chunks to embed; `0.3` vectors/metadata to `RagBase_<profile>`; `1` caller to LiteLLM with `model=vanilla-rag`; `2` alias to plugin; `3` question to embed; `4` dense `nearVector`, `k=5`; `5` chunks/scores; `6` question plus context to `light_gen`; `7` answer plus exact sources/metrics. Show host/Atlas boundaries and tuning for `k`, chunk profile, embed role, and generation role.

- [ ] **Step 4: Build Hybrid RAG HTML/SVG**

Messages: `1` alias route; `2` query embedding; `3` BM25+dense hybrid with `alpha=0.5`, `retrieve_k=20`; `4` fused candidates; `5` `{query,texts}` to TEI; dashed `5a` no-rerank bypass; `6` ordering and `top_n=5`; `7` context to `light_gen`; `8` answer/sources/metrics. Identify TEI as a cross-encoder, not an LLM.

- [ ] **Step 5: Embed and render both**

Add a numbered `Service-Aware Data Flow` subsection after Purpose in sections 3 and 4, embed PNG and link HTML, then shift later subsection numbers. Render with headless Chrome using `--window-size=1800,1000 --force-device-scale-factor=2`.

- [ ] **Step 6: Verify and commit Tasks 1-2**

Run focused approach/publication tests. Commit as `docs: add vanilla and hybrid flow diagrams` only when the created cases and nested-copy contract pass.

### Task 3: Create Contextual and Graph RAG Diagrams

**Files:**
- Create: `docs/diagrams/approaches/contextual-rag/data-flow.{html,png}`
- Create: `docs/diagrams/approaches/graph-rag/data-flow.{html,png}`
- Modify: `docs/approaches.md`

**Interfaces:**
- Consumes: contextual post-step, `RagContextual_<profile>`, Atlas ingestion, LightRAG roles/stores/profiles, Neo4j, and TEI adapter.
- Produces: index-time/query-time diagrams for both precomputed approaches.

- [ ] **Step 1: Build Contextual RAG HTML/SVG**

Ingestion: `0.1` parse/chunk; `0.2` document context plus chunk to `contextual_blurb`; `0.3` prefix response; `0.4` prefix plus chunk to embed; `0.5` vectors to `RagContextual_<profile>`. Query: alias, embedding, hybrid retrieval, TEI rerank, `light_gen`, structured evidence. Mark enrichment reusable and list retrieval plus blurb/chunk tuning.

- [ ] **Step 2: Build Graph RAG HTML/SVG**

Ingestion: `0.1` full docs/profile to LightRAG; `0.2` extraction prompts to EXTRACT; `0.3` entities/relations/summaries returned; `0.4` Neo4j plus vector/document/cache state. Query: `1` profile alias; `2` `/query` question/profile; `3` KEYWORD decomposition; `4` profile-controlled graph/vector retrieval; optional `5` TEI adapter; `6` context to QUERY role; `7` answer/profile metadata. State one shared graph, no showcase-authored fixed k-hop Cypher, and no exact returned contexts.

- [ ] **Step 3: Embed, render, inspect, test, and commit**

Add `### 5.2` and `### 6.2`, shift later numbers, render at 2x, inspect both lanes, run their tests plus `make docs-check`, and commit as `docs: add contextual and graph flow diagrams`.

### Task 4: Create Agentic and n8n Adaptive Diagrams

**Files:**
- Create: `docs/diagrams/approaches/agentic-rag/data-flow.{html,png}`
- Create: `docs/diagrams/approaches/n8n-adaptive-rag/data-flow.{html,png}`
- Modify: `docs/approaches.md`

**Interfaces:**
- Consumes: request-local ReAct history, vector/graph tools, n8n webhook, classifier, and downstream responses.
- Produces: loop-aware and policy-routing diagrams.

- [ ] **Step 1: Build Agentic RAG HTML/SVG**

Messages: `1` alias route; `2` system/user/tool schemas to agentic role; `3a` `search_vectors`; `3b` embed plus Weaviate hybrid retrieval; `4a` `query_graph`; `4b` LightRAG call; `5` observations with matching tool IDs appended to request history; `6` bounded repeat up to `max_steps`; `7` final answer plus trace. Show tool failures as observations, explicit loop exhaustion, and no persistence between queries.

- [ ] **Step 2: Build n8n Adaptive RAG HTML/SVG**

Messages: `1` alias route; `2` wrapper `POST {query}` to n8n webhook; `3` classifier prompt through LiteLLM; `4` simple/complex label; `5a` simple to Vanilla; `5b` complex to Agentic; `6` downstream answer/evidence; `7` shaped route/approach/evidence; `8` normalized response. Label timeout budgets and state that n8n is routing policy, not a retriever.

- [ ] **Step 3: Embed and renumber both sections**

Add `### 7.2` and `### 8.2`, shift later subsection numbers, and link each unique PNG/HTML pair.

- [ ] **Step 4: Render, inspect, test, and commit**

Render at 2x, inspect loop arrows and branch joins, run focused approach and three-surface tests, and commit as `docs: add agentic and adaptive flow diagrams`.

### Task 5: Create Experimental Lazy Graph Diagram

**Files:**
- Create: `docs/diagrams/approaches/lazy-graph-rag/data-flow.{html,png}`
- Modify: `docs/approaches.md`
- Modify: `docs/lazy-graph-rag.md`

**Interfaces:**
- Consumes: `RagBase_<profile>`, query embedding, full chunk reads, named-volume cache, deterministic concept graph, and `light_gen`.
- Produces: the seventh diagram and a cross-link from the dedicated Lazy Graph page.

- [ ] **Step 1: Build Lazy Graph HTML/SVG**

Messages: `0.1` base chunks/vectors to Weaviate; `1` alias route; `2` query embedding; concurrent `3a` hybrid seeds and `3b` full chunk read; `4` cache lookup keyed by collection/fingerprint/density; dashed `4a` deterministic cache-miss graph build with zero LLM calls; `5` relevance-budgeted expansion; `6` selected chunks to `light_gen`; `7` answer/exact sources/cache/index metadata. Label “No LightRAG” and “No Neo4j”.

- [ ] **Step 2: Embed and cross-link**

Add `### 9.1 Service-Aware Data Flow` to `docs/approaches.md`. Link the same diagram from `docs/lazy-graph-rag.md` without maintaining a duplicate image.

- [ ] **Step 3: Render and verify all seven cases**

Render the final PNG, inspect cache branches, then run `uv run pytest tests/test_approach_docs.py tests/docs/test_three_surface_docs.py -q`. Expect all source/image/embed/copy/link assertions to pass.

- [ ] **Step 4: Commit**

Commit as `docs: add lazy graph flow diagram`.

### Task 6: Update Diagram Index and Complete Visual Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/architecture.md`
- Modify: `docs/diagrams/approach-flows.md`
- Modify: `tests/test_approach_docs.py`

**Interfaces:**
- Consumes: seven complete diagram pairs.
- Produces: discoverable drill-down navigation and consistent seven-approach terminology.

- [ ] **Step 1: Add the drill-down index**

Add a seven-row table to `docs/architecture.md` with approach, purpose, PNG, and HTML links. Explain that the system diagram answers deployment, the parallel diagram answers comparison, and individual diagrams answer exact services/messages.

- [ ] **Step 2: Correct active-doc terminology**

Replace stale `six approach flow phases` wording with seven where Lazy Graph is present. Do not alter historical six-way experiment descriptions.

- [ ] **Step 3: Add index consistency tests**

Require all seven IDs in the drill-down section and reject stale six-approach wording in active README/diagram-index files.

- [ ] **Step 4: Inspect every PNG at original resolution**

Use `view_image` for all seven. Check clipping, overlaps, line-through-text, connected arrow heads/tails, ledger/arrow numbering, legend placement, and implementation accuracy. Fix HTML and rerender any failed image.

- [ ] **Step 5: Verify dimensions and commit**

Run `sips -g pixelWidth -g pixelHeight docs/diagrams/approaches/*/data-flow.png`; expect seven landscape images around `3600 x 2000`. Run targeted tests and commit as `docs: index per-approach flow diagrams`.

### Task 7: Full Verification, Review, and GitFlow Publication

**Files:**
- Verify all files changed by Tasks 1-6.

**Interfaces:**
- Consumes: complete feature branch.
- Produces: merged `develop` and `main`, published site/Wiki assets, and a clean branch/worktree state.

- [ ] **Step 1: Run full local verification**

```bash
uv run pytest tests backend_plugins/rag/tests -q
make docs-check
git diff --name-only -z -- '*.py' | xargs -0 uv run ruff check
git diff --check
```

Expected: all tests and docs pass; Ruff and whitespace checks are clean.

- [ ] **Step 2: Verify generated assets explicitly**

Confirm all fourteen nested files exist under `generated/site/assets/diagrams/approaches/` and `generated/wiki/diagrams/approaches/`, and generated approach-page links resolve.

- [ ] **Step 3: Obtain independent read-only review**

Review diagram accuracy, three-surface path handling, tests, and active-doc consistency. Resolve all Critical and Important findings and repeat verification.

- [ ] **Step 4: Open and merge the feature PR**

Push, open `codex/per-approach-data-flow-diagrams -> develop`, wait for required checks, merge, and delete the remote feature branch.

- [ ] **Step 5: Promote develop to main**

Open `develop -> main`, wait for checks, merge, then wait for the three-surface documentation workflow to succeed.

- [ ] **Step 6: Clean up and verify final state**

Fetch/prune, update local branches, remove the local feature branch, and verify only `main`/`develop` remain locally and remotely, no PRs are open, one clean worktree remains on `main`, and `main^{tree}` equals `develop^{tree}`.
