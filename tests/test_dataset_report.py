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
    # --stdout must emit exactly the bytes the write path produces (the committed
    # report), so `diff <(… --stdout) docs/dataset-complexity-report.md` is a
    # valid drift check — no extra trailing newline from print().
    assert out == (ROOT / "docs" / "dataset-complexity-report.md").read_text(encoding="utf-8")


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


def test_base_approach_ranked_last_is_not_framed_as_a_flavor_result(monkeypatch) -> None:
    # A canonical approach landing last in a flavorless regeneration must get the
    # neutral wording — the "flavor tuning result" framing is reserved for flavor
    # aliases. Current committed data takes the flavor branch, so drive this one
    # with synthetic snapshots.
    import compare.report_datasets as rd

    manifest = [{"id": "ds_a", "status": "measured", "complexity_level": 1,
                 "graph_nature": "none", "queries_file": "demo/queries.yaml",
                 "judgment_snapshot": "unused-a.json"},
                {"id": "ds_b", "status": "measured", "complexity_level": 2,
                 "graph_nature": "none", "queries_file": "demo/queries.yaml",
                 "judgment_snapshot": "unused-b.json"}]
    synthetic = {
        "unused-a.json": {"queries": [{"query_id": "q1", "observed_winner": "vanilla-rag",
                                       "mean_by_approach": {"vanilla-rag": 4.0,
                                                            "n8n-adaptive-rag": 2.0}}]},
        "unused-b.json": {"queries": [{"query_id": "q2", "observed_winner": "vanilla-rag",
                                       "mean_by_approach": {"vanilla-rag": 3.5,
                                                            "n8n-adaptive-rag": 1.5}}]},
    }
    monkeypatch.setattr(rd, "_load_manifest", lambda: manifest)
    monkeypatch.setattr(rd, "_load_judgments", lambda p: synthetic[p.name])

    report = rd.build_report()

    assert "Across the current snapshots, `n8n-adaptive-rag` ranked last" in report
    assert "flavor snapshots show one clear tuning result" not in report
    # graph-rag absent from these snapshots: no measurement claim about it at all
    assert "`graph-rag` is measured end to end" not in report


def test_graph_measured_claim_requires_graph_on_every_rung(monkeypatch) -> None:
    # "`graph-rag` is measured end to end across the live rungs" must require
    # graph-rag in EVERY measured snapshot: with a mixed set (one rung re-measured
    # via --approaches without graph-rag), the across-the-rungs claim is false for
    # the graph-less rung — say nothing instead, like the fully-absent case above.
    import compare.report_datasets as rd

    manifest = [{"id": "ds_a", "status": "measured", "complexity_level": 1,
                 "graph_nature": "none", "queries_file": "demo/queries.yaml",
                 "judgment_snapshot": "unused-a.json"},
                {"id": "ds_b", "status": "measured", "complexity_level": 2,
                 "graph_nature": "none", "queries_file": "demo/queries.yaml",
                 "judgment_snapshot": "unused-b.json"}]
    snapshots = {
        "unused-a.json": {"queries": [{"query_id": "q1", "observed_winner": "vanilla-rag",
                                       "mean_by_approach": {"vanilla-rag": 4.0,
                                                            "graph-rag": 2.0}}]},
        "unused-b.json": {"queries": [{"query_id": "q2", "observed_winner": "vanilla-rag",
                                       "mean_by_approach": {"vanilla-rag": 3.5,
                                                            "n8n-adaptive-rag": 1.5}}]},
    }
    monkeypatch.setattr(rd, "_load_manifest", lambda: manifest)
    monkeypatch.setattr(rd, "_load_judgments", lambda p: snapshots[p.name])

    report = rd.build_report()
    assert "`graph-rag` is measured end to end" not in report

    # With graph-rag present (and not leading) on every rung, the claim renders.
    snapshots["unused-b.json"] = {
        "queries": [{"query_id": "q2", "observed_winner": "vanilla-rag",
                     "mean_by_approach": {"vanilla-rag": 3.5, "graph-rag": 1.5}}]}
    report = rd.build_report()
    assert "`graph-rag` is measured end to end" in report
