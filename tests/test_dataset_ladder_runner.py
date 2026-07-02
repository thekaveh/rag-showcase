from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_start_all_supports_service_only_mode() -> None:
    script = (ROOT / "scripts" / "start-all.sh").read_text()

    assert "RAG_SHOWCASE_SKIP_DEFAULT_INGEST" in script
    assert "Skipping default corpus ingest" in script
    assert "Registering the six models" in script


def test_ladder_runner_exposes_measured_dataset_selection() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run-dataset-ladder.py", "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "--dataset" in result.stdout
    assert "--date-stamp" in result.stdout
    assert "--no-cold-reset" in result.stdout

