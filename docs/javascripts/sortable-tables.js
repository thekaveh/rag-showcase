(function () {
  "use strict";

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
    return [...records].sort(
      (left, right) =>
        compareValues(left[key], right[key], type, direction) || left.index - right.index,
    );
  }

  function matchesFilters(values, filters) {
    return Object.entries(filters).every(
      ([key, expected]) => !expected || values[key] === expected,
    );
  }

  function setSortState(headers, activeIndex, direction) {
    headers.forEach(({ cell }, index) => {
      if (index === activeIndex) {
        cell.setAttribute("aria-sort", direction === "asc" ? "ascending" : "descending");
      } else {
        cell.removeAttribute("aria-sort");
      }
    });
  }

  function createFilterControl(documentRef, table, name, values, onChange) {
    const id = `${table.id || "results-table"}-${name}-filter`;
    const label = documentRef.createElement("label");
    label.htmlFor = id;
    label.textContent = name[0].toUpperCase() + name.slice(1);

    const select = documentRef.createElement("select");
    select.id = id;
    select.name = name;
    const addOption = (labelText, value) => {
      const option = documentRef.createElement("option");
      option.value = value;
      option.textContent = labelText;
      select.append(option);
    };
    const plural = name === "approach" ? "approaches" : `${name}s`;
    addOption(`All ${plural}`, "");
    values.forEach((value) => addOption(value, value));
    select.addEventListener("change", onChange);

    label.append(select);
    return { label, select };
  }

  function enhanceTable(table) {
    if (table.dataset.sortableTablesEnhanced === "true") return;

    const documentRef = table.ownerDocument;
    const body = table.tBodies[0];
    const headerCells = Array.from(table.tHead ? table.tHead.rows[0].cells : []);
    if (!body || !headerCells.length) return;

    table.dataset.sortableTablesEnhanced = "true";
    const headers = headerCells.map((cell, index) => {
      const label = cell.textContent.trim();
      const button = documentRef.createElement("button");
      button.type = "button";
      button.className = "results-table__sort-button";
      button.textContent = label;
      button.title = `Sort by ${label}`;
      cell.replaceChildren(button);
      return {
        cell,
        index,
        type: cell.dataset.sortType || "text",
        preferredDirection: cell.dataset.sortDirection || "neutral",
        button,
      };
    });
    const records = Array.from(body.rows).map((row, index) => ({
      row,
      index,
      values: Array.from(row.cells, (cell) => cell.dataset.sortValue ?? cell.textContent.trim()),
      filters: {
        dataset: row.dataset.filterDataset || "",
        approach: row.dataset.filterApproach || "",
      },
    }));

    let datasetSelect;
    let approachSelect;
    const applyFilters = () => {
      const filters = {
        dataset: datasetSelect ? datasetSelect.value : "",
        approach: approachSelect ? approachSelect.value : "",
      };
      records.forEach((record) => {
        record.row.hidden = !matchesFilters(record.filters, filters);
      });
    };
    const restoreOrder = () => {
      records
        .slice()
        .sort((left, right) => left.index - right.index)
        .forEach((record) => body.append(record.row));
    };

    headers.forEach((header) => {
      header.button.addEventListener("click", () => {
        const wasActive = table.dataset.sortColumn === String(header.index);
        const direction = wasActive && table.dataset.sortDirection === "asc"
          ? "desc"
          : wasActive
            ? "asc"
            : header.preferredDirection === "higher"
              ? "desc"
              : "asc";
        const sorted = stableSort(
          records.map((record) => ({ ...record, value: record.values[header.index] })),
          "value",
          header.type,
          direction,
        );
        sorted.forEach((record) => body.append(record.row));
        table.dataset.sortColumn = String(header.index);
        table.dataset.sortDirection = direction;
        setSortState(headers, header.index, direction);
        applyFilters();
      });
    });

    if (table.dataset.filterable !== "true") return;

    const controls = documentRef.createElement("div");
    controls.className = "results-table-controls";
    controls.setAttribute("role", "group");
    const caption = table.caption ? table.caption.textContent.trim() : "Table";
    controls.setAttribute("aria-label", `${caption} filters`);
    const datasets = [...new Set(records.map((record) => record.filters.dataset).filter(Boolean))]
      .sort((left, right) => left.localeCompare(right));
    const approaches = [...new Set(records.map((record) => record.filters.approach).filter(Boolean))]
      .sort((left, right) => left.localeCompare(right));
    const datasetControl = createFilterControl(
      documentRef,
      table,
      "dataset",
      datasets,
      applyFilters,
    );
    datasetSelect = datasetControl.select;
    const approachControl = createFilterControl(
      documentRef,
      table,
      "approach",
      approaches,
      applyFilters,
    );
    approachSelect = approachControl.select;
    const resetButton = documentRef.createElement("button");
    resetButton.type = "button";
    resetButton.className = "results-table-controls__reset";
    resetButton.textContent = "Reset";
    resetButton.addEventListener("click", () => {
      datasetSelect.value = "";
      approachSelect.value = "";
      restoreOrder();
      delete table.dataset.sortColumn;
      delete table.dataset.sortDirection;
      setSortState(headers, -1, "asc");
      applyFilters();
    });
    controls.append(datasetControl.label, approachControl.label, resetButton);
    table.parentNode.insertBefore(controls, table);
  }

  const api = { compareValues, stableSort, matchesFilters, enhanceTable };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document !== "undefined") {
    const initialize = () => document.querySelectorAll(".results-table").forEach(enhanceTable);
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
      initialize();
    }
  }
})();
