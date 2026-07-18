const test = require("node:test");
const assert = require("node:assert/strict");
const tables = require("../../docs/javascripts/sortable-tables.js");

class FakeElement {
  constructor(tagName, text = "") {
    this.tagName = tagName.toUpperCase();
    this._text = text;
    this.attributes = new Map();
    this.children = [];
    this.dataset = {};
    this.listeners = new Map();
    this.hidden = false;
    this.parentNode = null;
    this.rows = this.children;
    this.value = "";
  }

  get textContent() {
    return this._text + this.children.map((child) => child.textContent).join("");
  }

  set textContent(value) {
    this._text = String(value);
    this.children.length = 0;
  }

  append(...children) {
    children.forEach((child) => {
      if (child.parentNode) {
        const index = child.parentNode.children.indexOf(child);
        if (index >= 0) child.parentNode.children.splice(index, 1);
      }
      child.parentNode = this;
      this.children.push(child);
    });
  }

  replaceChildren(...children) {
    this.children.forEach((child) => {
      child.parentNode = null;
    });
    this.children.length = 0;
    this._text = "";
    this.append(...children);
  }

  insertBefore(child, reference) {
    if (child.parentNode) {
      const oldIndex = child.parentNode.children.indexOf(child);
      if (oldIndex >= 0) child.parentNode.children.splice(oldIndex, 1);
    }
    child.parentNode = this;
    const index = this.children.indexOf(reference);
    this.children.splice(index < 0 ? this.children.length : index, 0, child);
  }

  addEventListener(type, listener) {
    this.listeners.set(type, listener);
  }

  trigger(type) {
    this.listeners.get(type)({ target: this, type });
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  getAttribute(name) {
    return this.attributes.has(name) ? this.attributes.get(name) : null;
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }
}

class FakeDocument {
  createElement(tagName) {
    return new FakeElement(tagName);
  }
}

function fixtureRow(documentRef, id, dataset, approach, score) {
  const row = documentRef.createElement("tr");
  row.id = id;
  row.dataset.filterDataset = dataset;
  row.dataset.filterApproach = approach;
  row.cells = [dataset, approach, score].map((value) => {
    const cell = documentRef.createElement("td");
    cell.dataset.sortValue = value;
    cell.textContent = value;
    return cell;
  });
  return row;
}

function sortableTableFixture() {
  const documentRef = new FakeDocument();
  const container = documentRef.createElement("section");
  const table = documentRef.createElement("table");
  table.id = "fixture-results";
  table.ownerDocument = documentRef;
  table.dataset.filterable = "true";
  table.caption = documentRef.createElement("caption");
  table.caption.textContent = "Fixture results";
  const headerRow = documentRef.createElement("tr");
  const headers = [
    ["Dataset", "text", "neutral"],
    ["Approach", "text", "neutral"],
    ["Score", "number", "higher"],
  ].map(([label, type, direction]) => {
    const header = documentRef.createElement("th");
    header.textContent = label;
    header.dataset.sortType = type;
    header.dataset.sortDirection = direction;
    return header;
  });
  headerRow.cells = headers;
  table.tHead = { rows: [headerRow] };
  const body = documentRef.createElement("tbody");
  body.rows = body.children;
  table.tBodies = [body];
  [
    ["generator-1", "baseline_curated", "vanilla-rag", "2"],
    ["generator-2", "graph_native", "graph-rag", "1"],
    ["generator-3", "graph_native", "vanilla-rag", "3"],
    ["generator-4", "baseline_curated", "graph-rag", "4"],
  ].forEach(([id, dataset, approach, score]) => {
    body.append(fixtureRow(documentRef, id, dataset, approach, score));
  });
  container.append(table);
  return { body, container, headers, table };
}

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

test("text sorting is case-insensitive, stable, and keeps missing values last", () => {
  const rows = [
    { value: null, index: 0 },
    { value: "banana", index: 1 },
    { value: "Apple", index: 2 },
    { value: "apple", index: 3 },
  ];

  assert.deepEqual(
    tables.stableSort(rows, "value", "text", "asc").map((row) => row.index),
    [2, 3, 1, 0],
  );
  assert.deepEqual(
    tables.stableSort(rows, "value", "text", "desc").map((row) => row.index),
    [1, 2, 3, 0],
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

test("DOM filters combine and reset restores the original sortable table", () => {
  const { body, container, headers, table } = sortableTableFixture();

  tables.enhanceTable(table);
  const controls = container.children[0];
  const [datasetLabel, approachLabel, resetButton] = controls.children;
  const datasetSelect = datasetLabel.children[0];
  const approachSelect = approachLabel.children[0];
  const scoreButton = headers[2].children[0];

  assert.equal(approachSelect.children[0].textContent, "All approaches");

  scoreButton.trigger("click");
  assert.deepEqual(body.rows.map((row) => row.id), [
    "generator-4",
    "generator-3",
    "generator-1",
    "generator-2",
  ]);
  assert.equal(headers[2].getAttribute("aria-sort"), "descending");

  datasetSelect.value = "graph_native";
  datasetSelect.trigger("change");
  approachSelect.value = "vanilla-rag";
  approachSelect.trigger("change");
  assert.deepEqual(
    body.rows.filter((row) => !row.hidden).map((row) => row.id),
    ["generator-3"],
  );

  resetButton.trigger("click");
  assert.equal(datasetSelect.value, "");
  assert.equal(approachSelect.value, "");
  assert.deepEqual(body.rows.map((row) => row.id), [
    "generator-1",
    "generator-2",
    "generator-3",
    "generator-4",
  ]);
  assert.ok(body.rows.every((row) => !row.hidden));
  assert.ok(headers.every((header) => header.getAttribute("aria-sort") === null));
  assert.ok(headers.every((header) => header.children[0].tagName === "BUTTON"));
  assert.equal(table.dataset.sortColumn, undefined);
  assert.equal(table.dataset.sortDirection, undefined);

  scoreButton.trigger("click");
  assert.equal(headers[2].getAttribute("aria-sort"), "descending");
});
