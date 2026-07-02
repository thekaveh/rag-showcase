from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_dataset_adapter_scripts_expose_help() -> None:
    scripts = [
        "corpus/adapters/stark_export.py",
        "corpus/adapters/openalex_scholarly.py",
        "corpus/adapters/gdelt_events.py",
        "corpus/adapters/cyber_threat_intel.py",
    ]

    for script in scripts:
        result = subprocess.run(
            [sys.executable, script, "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=True,
        )
        assert "usage:" in result.stdout
        assert "--output" in result.stdout
