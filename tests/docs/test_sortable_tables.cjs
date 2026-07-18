const test = require("node:test");
const assert = require("node:assert/strict");
const tables = require("../../docs/javascripts/sortable-tables.js");

test("missing values sort after numeric values in both directions", () => {
  const rows = [
    { value: null, index: 0 },
    { value: 2, index: 1 },
    { value: 5, index: 2 },
  ];

  assert.deepEqual(
    tables.stableSort(rows, "value", "number", "asc").map((row) => row.value),
    [2, 5, null],
  );
  assert.deepEqual(
    tables.stableSort(rows, "value", "number", "desc").map((row) => row.value),
    [5, 2, null],
  );
});

test("stable sort preserves generator order for ties", () => {
  const rows = [
    { value: 3, index: 2 },
    { value: 3, index: 0 },
    { value: 3, index: 1 },
  ];

  assert.deepEqual(
    tables.stableSort(rows, "value", "number", "asc").map((row) => row.index),
    [0, 1, 2],
  );
});

test("filters combine dataset and approach", () => {
  assert.equal(
    tables.matchesFilters(
      { dataset: "graph_native", approach: "graph-rag" },
      { dataset: "graph_native", approach: "graph-rag" },
    ),
    true,
  );
  assert.equal(
    tables.matchesFilters(
      { dataset: "baseline_curated", approach: "graph-rag" },
      { dataset: "graph_native", approach: "graph-rag" },
    ),
    false,
  );
});
