# Post-Review Cleanup Report

## Changes Applied

### 1. `tests/test_demo_matrix.py`
- Removed unused `import yaml` line.
- In `test_all_models_registered`: split the `/v1/models` GET into a named variable `r`, added `r.raise_for_status()` before `r.json()`.

### 2. `backend_plugins/rag/common/vectors.py`
- In `search_dense`: removed `return_metadata=wq.MetadataQuery(distance=True)` from `coll.query.near_vector(...)`. Call is now `coll.query.near_vector(near_vector=query_vec, limit=k)`. `search_hybrid` unchanged.

### 3. `backend_plugins/rag/tests/test_openai_io.py`
- Added `test_build_response_handles_empty_sources`: calls `build_response("m", "ans", [], Metrics(0.5, 0, 1, 0))`, asserts `object == "chat.completion"` and `"ans"` in content.
- Added `test_build_response_source_without_score`: calls `build_response("m", "ans", [Source("T", "snip")], Metrics(0.5, 1, 1, 0))` (score defaults to None), asserts "T" and "snip" appear in content, and "score" does NOT appear in the rendered `<details>` source block.

### 4. `backend_plugins/rag/roles.yaml`
- Added trailing comment on `extraction:` line: `# consumed by LightRAG (Atlas-side), not read by this plugin`

## Test Commands and Output

```
$ uv run pytest backend_plugins/rag/tests -q
..................
18 passed in 0.37s

$ uv run pytest tests/ -q
ssssssss
8 skipped in 0.02s
```

All unit tests green (18 passed). Integration tests skip cleanly (8 skipped — stack down as expected).
