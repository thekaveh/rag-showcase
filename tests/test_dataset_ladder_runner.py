from __future__ import annotations

import json
import subprocess
import sys
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _load_ladder_module():
    # The hyphenated filename keeps the script un-importable by name; load it the
    # way Python would execute it.
    spec = importlib.util.spec_from_file_location(
        "run_dataset_ladder", ROOT / "scripts" / "run-dataset-ladder.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_start_all_supports_service_only_mode() -> None:
    script = (ROOT / "scripts" / "start-all.sh").read_text(encoding="utf-8")

    assert "--n8n-source" not in script
    assert "--minio-source container" in script
    assert "RAG_SHOWCASE_SKIP_DEFAULT_INGEST" in script
    assert "Skipping default corpus ingest" in script
    assert "Registering RAG models and flavor aliases" in script
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
    assert "--flavors" in result.stdout
    assert "--include-candidates" in result.stdout


def test_overlay_passes_lightrag_ollama_context_caps() -> None:
    overlay = (ROOT / "compose" / "rag-overlay.yml").read_text(encoding="utf-8")

    assert "asset-baker: !reset null" in overlay
    assert "EXTRACT_OLLAMA_LLM_NUM_CTX" in overlay
    assert "KEYWORD_OLLAMA_LLM_NUM_CTX" in overlay
    assert "QUERY_OLLAMA_LLM_NUM_CTX" in overlay
    assert "RAG_FLAVORS_FILE" in overlay
    assert "../n8n:/showcase-n8n:ro" in overlay


def test_ladder_runner_rejects_failed_matrix_cells() -> None:
    module = _load_ladder_module()

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


def test_ladder_runner_can_select_candidate_dataset_when_enabled(monkeypatch) -> None:
    module = _load_ladder_module()

    manifest = {
        "datasets": [
            {"id": "measured_a", "status": "measured"},
            {"id": "candidate_b", "status": "candidate"},
        ]
    }
    monkeypatch.setattr(module, "load_manifest", lambda: manifest)

    selected = module.selected_datasets(["candidate_b"], include_candidates=True)
    assert [d["id"] for d in selected] == ["candidate_b"]

    # --include-candidates without --dataset must NOT silently expand the default
    # run set to every candidate rung (its help text scopes it to --dataset).
    default = module.selected_datasets(None, include_candidates=True)
    assert [d["id"] for d in default] == ["measured_a"]

    # A candidate id without the flag names the flag in the error.
    with pytest.raises(SystemExit, match="include-candidates"):
        module.selected_datasets(["candidate_b"], include_candidates=False)


def test_ladder_runner_rejects_judgments_without_valid_verdicts() -> None:
    module = _load_ladder_module()

    good = {"queries": [{"query_id": "a", "mean_by_approach": {"vanilla-rag": 4.0}}]}
    module.validate_judgments(good, dataset_id="example")  # must not raise

    empty_means = {"queries": [{"query_id": "a", "mean_by_approach": {}},
                               {"query_id": "b", "mean_by_approach": {"x": 1.0}}]}
    with pytest.raises(RuntimeError, match="example.*a"):
        module.validate_judgments(empty_means, dataset_id="example")

    with pytest.raises(RuntimeError, match="no queries"):
        module.validate_judgments({"queries": []}, dataset_id="example")


def test_wait_for_lightrag_drains_only_when_nothing_pending(monkeypatch) -> None:
    module = _load_ladder_module()
    monkeypatch.setattr(module.time, "sleep", lambda s: None)

    # busy -> not busy but docs still PENDING (the enqueue/pickup gap) -> drained
    status_seq = iter([{"busy": True}, {"busy": False}, {"busy": False}])
    docs_seq = iter([{"statuses": {"PENDING": ["d1"]}}, {"statuses": {"PROCESSED": ["d1"]}}])
    monkeypatch.setattr(module, "lightrag_status", lambda: next(status_seq))
    monkeypatch.setattr(module, "lightrag_documents", lambda: next(docs_seq))
    module.wait_for_lightrag("ds")  # returns without raising

    # failed documents must raise
    monkeypatch.setattr(module, "lightrag_status", lambda: {"busy": False})
    monkeypatch.setattr(module, "lightrag_documents",
                        lambda: {"statuses": {"failed": ["d9"]}})
    with pytest.raises(RuntimeError, match="failed documents"):
        module.wait_for_lightrag("ds")


def test_wait_for_lightrag_tolerates_transient_poll_failures(monkeypatch) -> None:
    # One flaky docker-exec poll must not abort a multi-hour ladder run; three in
    # a row must.
    import subprocess as sp
    module = _load_ladder_module()
    monkeypatch.setattr(module.time, "sleep", lambda s: None)

    calls = {"n": 0}
    def flaky_status():
        calls["n"] += 1
        if calls["n"] <= 2:
            raise sp.CalledProcessError(1, ["docker", "exec"])
        return {"busy": False}
    monkeypatch.setattr(module, "lightrag_status", flaky_status)
    monkeypatch.setattr(module, "lightrag_documents", lambda: {"statuses": {}})
    module.wait_for_lightrag("ds")  # two failures tolerated, then drains
    assert calls["n"] == 3

    def always_broken():
        raise sp.CalledProcessError(1, ["docker", "exec"])
    monkeypatch.setattr(module, "lightrag_status", always_broken)
    with pytest.raises(RuntimeError, match="3 times in a row"):
        module.wait_for_lightrag("ds")


def test_wait_for_lightrag_tolerates_flaky_documents_poll(monkeypatch) -> None:
    # The DOCUMENTS probe shares the flakiness profile of the status probe and
    # must sit inside the same tolerance window — moving it back outside the
    # try (the original exposure) fails this test.
    import subprocess as sp
    module = _load_ladder_module()
    monkeypatch.setattr(module.time, "sleep", lambda s: None)

    monkeypatch.setattr(module, "lightrag_status", lambda: {"busy": False})
    calls = {"n": 0}
    def flaky_documents():
        calls["n"] += 1
        if calls["n"] <= 2:
            raise sp.CalledProcessError(1, ["docker", "exec"], stderr="boom")
        return {"statuses": {}}
    monkeypatch.setattr(module, "lightrag_documents", flaky_documents)
    module.wait_for_lightrag("ds")  # two failures tolerated, then drains
    assert calls["n"] == 3


def test_ladder_rejects_unknown_selection_before_any_destructive_step(monkeypatch) -> None:
    # A typo'd --approaches/--flavors must fail in validate_selections — not an
    # hour later when run_matrix launches after the cold reset + ingest.
    module = _load_ladder_module()

    module.validate_selections("vanilla-rag,graph-rag-wide", "")  # valid: no raise
    module.validate_selections("", "default,graph-rag")           # valid: no raise

    with pytest.raises(SystemExit, match="vanila-rag"):
        module.validate_selections("vanila-rag", "")
    with pytest.raises(SystemExit, match="nope-flavor"):
        module.validate_selections("", "nope-flavor")


def test_selection_validation_uses_the_manifest_run_matrix_will_use(monkeypatch, tmp_path) -> None:
    # MATRIX_FLAVORS_FILE reaches run_matrix through the inherited env; the
    # pre-validation must resolve the SAME manifest, or a custom alias is falsely
    # rejected up front (and a default-only alias would die after the cold reset).
    module = _load_ladder_module()
    custom = tmp_path / "flavors.yaml"
    custom.write_text(
        "flavors:\n  - alias: hybrid-rag-custom\n    base: hybrid-rag\n"
        "    params:\n      retrieve_k: 12\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MATRIX_FLAVORS_FILE", str(custom))
    module.validate_selections("hybrid-rag-custom", "")  # valid in the custom manifest

    monkeypatch.delenv("MATRIX_FLAVORS_FILE", raising=False)
    with pytest.raises(SystemExit, match="hybrid-rag-custom"):
        module.validate_selections("hybrid-rag-custom", "")  # not in the default one


def test_run_matrix_and_judge_ignores_exported_selection_env(monkeypatch, tmp_path) -> None:
    # MATRIX_MODELS/MATRIX_FLAVORS exported in the caller's shell (e.g. left over
    # from the documented manual `MATRIX_MODELS=... run_matrix.py` workflow) must
    # not reach the subprocess when the flags are omitted: they'd bypass
    # validate_selections() and silently narrow a snapshot stamped "measured", or
    # abort only after the cold reset + ingest. Only the validated CLI flags set
    # them — unlike MATRIX_FLAVORS_FILE, whose inheritance is deliberate (above).
    module = _load_ladder_module()
    monkeypatch.setenv("MATRIX_MODELS", "stale-export")
    monkeypatch.setenv("MATRIX_FLAVORS", "stale-export")
    monkeypatch.setattr(module, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(module, "DOC_RESULTS", tmp_path / "doc-results")
    module.RESULTS.mkdir(parents=True)

    seen_envs: list[dict] = []
    def fake_run(cmd, env=None, **kw):
        env = dict(env or {})
        seen_envs.append(env)
        if "MATRIX_RESULTS_FILE" in env:
            (module.RESULTS / env["MATRIX_RESULTS_FILE"]).write_text(json.dumps(
                {"cells": [{"query_id": "q1", "model": "vanilla-rag", "ok": True}]}),
                encoding="utf-8")
        else:
            (module.RESULTS / env["JUDGE_RESULTS_FILE"]).write_text(json.dumps(
                {"queries": [{"query_id": "q1", "mean_by_approach": {"vanilla-rag": 4.0}}]}),
                encoding="utf-8")
    monkeypatch.setattr(module, "run", fake_run)

    module.run_matrix_and_judge({"id": "ds", "queries_file": "q.json"}, "2026-07-04",
                                approaches="", flavors="")
    matrix_env = seen_envs[0]
    assert matrix_env["MATRIX_QUERIES_FILE"] == "q.json"
    assert "MATRIX_MODELS" not in matrix_env
    assert "MATRIX_FLAVORS" not in matrix_env

    # The validated flags must still reach the subprocess (the scrub above must
    # not eat them).
    module.run_matrix_and_judge({"id": "ds2", "queries_file": "q.json"}, "2026-07-04",
                                approaches="vanilla-rag", flavors="graph-rag-wide")
    matrix_env = seen_envs[2]
    assert matrix_env["MATRIX_MODELS"] == "vanilla-rag"
    assert matrix_env["MATRIX_FLAVORS"] == "graph-rag-wide"


def test_selection_validation_resolves_relative_manifest_against_repo_root(
        monkeypatch, tmp_path) -> None:
    # run() launches run_matrix with cwd=ROOT, so a relative MATRIX_FLAVORS_FILE
    # (the documented form) resolves against the repo root in the child. The
    # pre-validation must resolve it the same way even when the ladder itself is
    # launched from another cwd — a missing manifest silently degrades to
    # base-only profiles, falsely rejecting the custom alias up front.
    module = _load_ladder_module()
    (tmp_path / "custom").mkdir()
    (tmp_path / "custom" / "flavors.yaml").write_text(
        "flavors:\n  - alias: hybrid-rag-custom\n    base: hybrid-rag\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setenv("MATRIX_FLAVORS_FILE", "custom/flavors.yaml")
    monkeypatch.chdir(tmp_path / "custom")  # anywhere that is not ROOT

    module.validate_selections("hybrid-rag-custom", "")  # must not falsely reject
