from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dataset_report_ranks_measured_inputs_by_dataset() -> None:
    result = subprocess.run(
        [sys.executable, "compare/report_datasets.py", "--stdout"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    out = result.stdout
    assert "## 1. Dataset Complexity Ladder" in out
    assert "| Dataset | Complexity | Status | Winner | Ranking |" in out
    assert "baseline_curated" in out
    assert "graph_native" in out
    assert "contextual-rag" in out
    assert "on `graph_native`, `hybrid-rag-high-recall` leads" in out
    assert "on `cyber_threat_intel`, `contextual-rag-high-recall` leads" in out
    assert "## 3. Per-Query Winners" in out
    assert "stark_prime" in out
    assert "pending live run" in out


def test_dataset_report_write_mode_updates_documentation() -> None:
    result = subprocess.run(
        [sys.executable, "compare/report_datasets.py", "--output", "docs/dataset-complexity-report.md"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "wrote docs/dataset-complexity-report.md" in result.stdout
    report = (ROOT / "docs" / "dataset-complexity-report.md").read_text()
    assert "## 1. Dataset Complexity Ladder" in report
    assert "## 2. Ranking Drift by Input Dataset" in report
    assert "## 3. Per-Query Winners" in report
