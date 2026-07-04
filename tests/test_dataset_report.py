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


def test_dataset_report_write_mode_matches_committed_documentation(tmp_path) -> None:
    # Generate to a tmp path (a test must not mutate the tracked tree) and require
    # byte-equality with the committed report — this is the drift guard that catches
    # a generator or manifest change whose regenerated output was never committed.
    out = tmp_path / "report.md"
    result = subprocess.run(
        [sys.executable, "compare/report_datasets.py", "--output", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert f"wrote {out}" in result.stdout
    generated = out.read_text(encoding="utf-8")
    assert "## 1. Dataset Complexity Ladder" in generated
    assert "## 2. Ranking Drift by Input Dataset" in generated
    assert "## 3. Per-Query Winners" in generated
    committed = (ROOT / "docs" / "dataset-complexity-report.md").read_text(encoding="utf-8")
    assert generated == committed, (
        "docs/dataset-complexity-report.md is stale — regenerate it with "
        "`uv run python compare/report_datasets.py --output docs/dataset-complexity-report.md`"
    )


def test_dataset_report_write_mode_accepts_absolute_out_of_repo_path(tmp_path) -> None:
    # An absolute --output outside the repo used to crash the confirmation print via
    # Path.relative_to(ROOT) — AFTER the file was already written. The guard must keep
    # the CLI at exit 0 and fall back to printing the full path.
    out = tmp_path / "report.md"  # absolute, outside ROOT
    result = subprocess.run(
        [sys.executable, "compare/report_datasets.py", "--output", str(out)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert result.returncode == 0
    assert out.read_text(encoding="utf-8").startswith("# Dataset Complexity Report")
    assert f"wrote {out}" in result.stdout
