from __future__ import annotations

import subprocess
import sys
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_start_all_supports_service_only_mode() -> None:
    script = (ROOT / "scripts" / "start-all.sh").read_text()

    assert "RAG_SHOWCASE_SKIP_DEFAULT_INGEST" in script
    assert "Skipping default corpus ingest" in script
    assert "Registering the six models" in script
    assert "import:workflow" in script
    assert "--activeState=fromJson" in script
    assert "adaptive-rag.workflow.json" in script


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


def test_overlay_passes_lightrag_ollama_context_caps() -> None:
    overlay = (ROOT / "compose" / "rag-overlay.yml").read_text()

    assert "EXTRACT_OLLAMA_LLM_NUM_CTX" in overlay
    assert "KEYWORD_OLLAMA_LLM_NUM_CTX" in overlay
    assert "QUERY_OLLAMA_LLM_NUM_CTX" in overlay
    assert "../n8n:/showcase-n8n:ro" in overlay


def test_ladder_runner_rejects_failed_matrix_cells() -> None:
    spec = importlib.util.spec_from_file_location(
        "run_dataset_ladder", ROOT / "scripts" / "run-dataset-ladder.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    matrix = {
        "cells": [
            {"query_id": "ok", "model": "vanilla-rag", "ok": True},
            {"query_id": "bad", "model": "n8n-adaptive-rag", "ok": False, "error": "500"},
        ]
    }

    try:
        module.validate_matrix_cells(matrix, dataset_id="example")
    except RuntimeError as exc:
        assert "example" in str(exc)
        assert "n8n-adaptive-rag" in str(exc)
        assert "bad" in str(exc)
    else:
        raise AssertionError("validate_matrix_cells accepted a failed matrix cell")
