from __future__ import annotations

import json
import subprocess
import sys
import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JUDGES = ["qwen3.6:latest", "gemma4:31b"]


def _canonical_fixture(dataset_id: str, row_id: str) -> dict:
    hashes = {
        "evaluation_manifest": "a", "dataset_questions": "b", "flavors": "c",
        "roles": "d", "consumer_manifest": "e", "atlas_env_user": "f",
        "runtime_model_inventory": "g", "lightrag_query_profiles": "h",
    }
    runtime = {
        "project": "rag-showcase", "base_port": 22000,
        "provider_sources": {"llm": "ollama-localhost", "comfyui": "disabled"},
        "rag_showcase": {
            "commit": "repo", "tree": "repo-tree", "dirty": True,
            "patch_sha256": "repo-patch", "patch_capture": "exact",
        },
        "atlas": {
            "commit": "atlas", "tree": "atlas-tree", "dirty": False,
            "patch_sha256": "atlas-patch", "patch_capture": "exact",
        },
        "judge_panel": {
            "endpoint": "atlas-litellm", "models": DEFAULT_JUDGES,
            "thinking": False,
        },
        "runtime_files": {
            "model_inventory": {"sha256": "models", "entries": ["vanilla-rag"]},
            "lightrag_query_profiles": {"sha256": "profiles", "entries": ["graph-rag"]},
        },
    }
    return {
        "row_id": row_id, "dataset": {"id": dataset_id}, "status": "ok",
        "question": {"id": "q1"}, "approach": {"model": "vanilla-rag"},
        "reproducibility": {"config_hashes": hashes, "runtime": runtime},
        "metrics": {"ragas": {
            "status": "ok", "requested": ["faithfulness", "answer_relevancy"],
            "scores": {"faithfulness": 0.8, "answer_relevancy": 0.8},
        }},
    }


def _judgments_fixture(dataset_id: str) -> dict:
    scores = {"vanilla-rag": 4.0}
    return {
        "status": "ok", "dataset_id": dataset_id, "judges": DEFAULT_JUDGES,
        "runtime": {"backend": "atlas-litellm", "endpoint": "atlas-litellm"},
        "queries": [{
            "query_id": "q1", "mean_by_approach": scores,
            "per_judge": {judge: {"scores": scores} for judge in DEFAULT_JUDGES},
        }],
    }


def _summary_fixture(dataset_id: str) -> dict:
    return {
        "schema_version": 1,
        "datasets": {dataset_id: {
            "coverage": {"total_rows": 1, "ok": 1, "errors": 0, "timeouts": 0},
            "judge_panel": {
                "status": "ok", "models": DEFAULT_JUDGES,
                "evaluated_queries": 1, "total_queries": 1,
            },
        }},
    }


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


def test_evaluation_contract_requires_explicit_judge_models(monkeypatch) -> None:
    module = _load_ladder_module()
    monkeypatch.delenv("JUDGE_MODELS", raising=False)
    monkeypatch.delenv("MATRIX_MANIFEST_FILE", raising=False)

    with pytest.raises(RuntimeError, match="JUDGE_MODELS"):
        module.evaluation_contract(dict())


def test_start_all_supports_service_only_mode() -> None:
    script = (ROOT / "scripts" / "start-all.sh").read_text(encoding="utf-8")

    assert "--n8n-source" not in script
    assert "--minio-source" not in script
    assert "--no-tui --detach" in script
    assert "atlas_preflight.py" not in script
    assert "ATLAS_START_PID" not in script
    assert "RAG_SHOWCASE_SKIP_DEFAULT_INGEST" in script
    assert "Skipping default corpus ingest" in script
    assert "RAG_INGESTION_PROFILE" in script
    assert "*[!a-z0-9._-]*|[._-]*" in script
    assert "ingest.atlas_job" in script
    assert 'BACKEND_INTERNAL_API_TOKEN="$(envval BACKEND_INTERNAL_API_TOKEN)"' in script
    assert "ingest.contextual" in script
    assert "/app/ingest/ingest.py" not in script
    assert "Reconciling Atlas-declared LiteLLM model aliases" not in script
    assert "import:workflow" not in script
    assert "--activeState=fromJson" not in script
    assert "adaptive-rag.workflow.json" not in script
    assert '--project "$ATLAS_PROJECT_NAME"' in script
    assert '--base-port "$ATLAS_BASE_PORT"' in script
    assert "RAG_SHOWCASE_LLM_PROVIDER_SOURCE" in script
    assert "RAG_SHOWCASE_COMFYUI_SOURCE" in script
    assert "ATLAS_SOURCE_ARGS" in script
    assert "--llm-provider-source ollama-localhost" not in script
    assert "--comfyui-source disabled" not in script
    assert "select_atlas_base_port.py" not in script
    assert '--base-port "$ATLAS_BASE_PORT"' in script
    assert "Atlas #654" not in script
    assert "sync_bootstrap_env_key" not in script


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
    assert "--include-flavor-tier" in result.stdout
    assert "--include-candidates" in result.stdout
    normalized = " ".join(result.stdout.split())
    assert "Defaults to the canonical six approaches" in normalized
    assert "all seven base approaches" in normalized


def test_overlay_passes_lightrag_ollama_context_caps() -> None:
    overlay = (ROOT / "compose" / "rag-overlay.yml").read_text(encoding="utf-8")

    assert "asset-baker" not in overlay
    assert "EXTRACT_OLLAMA_LLM_NUM_CTX" in overlay
    assert "KEYWORD_OLLAMA_LLM_NUM_CTX" in overlay
    assert "QUERY_OLLAMA_LLM_NUM_CTX" in overlay
    assert "RAG_FLAVORS_FILE" in overlay
    assert "RAG_BASE_COLLECTION" in overlay
    assert "RAG_CONTEXTUAL_COLLECTION" in overlay
    assert "../n8n:/showcase-n8n:ro" not in overlay


def test_ladder_starts_profile_scoped_collections(monkeypatch) -> None:
    module = _load_ladder_module()
    seen: list[dict[str, str]] = []
    monkeypatch.setattr(module, "run", lambda cmd, env=None: seen.append(dict(env or {})))

    module.start_service_only({"ingestion_profile": "graph_native"})

    assert seen[0]["RAG_INGESTION_PROFILE"] == "graph_native"
    assert seen[0]["RAG_BASE_COLLECTION"] == "RagBase_graph_native"
    assert seen[0]["RAG_CONTEXTUAL_COLLECTION"] == "RagContextual_graph_native"


def test_ladder_uses_atlas_job_then_contextual_post_step(monkeypatch, tmp_path) -> None:
    module = _load_ladder_module()
    (tmp_path / "corpus" / "subset").mkdir(parents=True)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    commands: list[list[str]] = []
    record = {
        "id": "ing-1",
        "profile": "baseline_curated",
        "revision": "rev-1",
        "content_digest": "digest-1",
        "status": "completed",
        "phases": [{"name": "finalize", "status": "completed"}],
    }
    monkeypatch.setattr(module, "envval", lambda key, default="": "63093")
    monkeypatch.setattr(module, "project_name", lambda: "rag-showcase")
    captured_env: list[dict[str, str]] = []
    monkeypatch.setattr(
        module,
        "capture_json",
        lambda cmd, env=None: commands.append(cmd) or captured_env.append(env or {}) or record,
    )
    monkeypatch.setattr(module, "run", lambda cmd, env=None: commands.append(cmd))

    actual = module.ingest_dataset(
        {
            "id": "baseline_curated",
            "ingestion_profile": "baseline_curated",
            "corpus_path": "corpus/subset",
        }
    )

    assert actual == record
    assert commands[0][:5] == ["uv", "run", "python", "-m", "ingest.atlas_job"]
    assert "--profile" in commands[0]
    assert "baseline_curated" in commands[0]
    assert "http://127.0.0.1:63093" in commands[0]
    assert captured_env[0]["BACKEND_INTERNAL_API_TOKEN"] == "63093"
    assert "LIGHTRAG_API_KEY" not in captured_env[0]
    assert "--lightrag-url" not in commands[0]
    assert commands[1] == [
        "docker",
        "exec",
        "-e",
        "PYTHONPATH=/app/plugins:/app",
        "rag-showcase-backend",
        "python",
        "-m",
        "ingest.contextual",
    ]
    assert commands[2] == [
        "uv",
        "run",
        "python",
        "scripts/verify_adaptive_webhook.py",
        "--url",
        "http://127.0.0.1:63093/webhook/adaptive-rag",
    ]


def test_cold_reset_targets_only_rag_showcase(monkeypatch) -> None:
    module = _load_ladder_module()
    seen = []
    monkeypatch.setattr(module.subprocess, "run", lambda cmd, **kwargs: seen.append((cmd, kwargs)))

    module.cold_reset()

    assert seen[0][0] == ["./scripts/stop-all.sh", "--cold"]
    assert seen[0][1]["cwd"] == ROOT


def test_capture_json_preserves_child_failure_details(monkeypatch) -> None:
    module = _load_ladder_module()
    monkeypatch.setattr(
        module.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args[0], 1, stdout="", stderr="backend returned 401"
        ),
    )

    with pytest.raises(RuntimeError, match="backend returned 401"):
        module.capture_json(["failing-command"])


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

    good = {
        "status": "ok",
        "judges": ["judge-a", "judge-b"],
        "runtime": {"backend": "atlas-litellm", "endpoint": "atlas-litellm"},
        "queries": [
            {
                "query_id": "a",
                "mean_by_approach": {"vanilla-rag": 4.0},
                "per_judge": {
                    "judge-a": {"scores": {"vanilla-rag": 4.0}},
                    "judge-b": {"scores": {"vanilla-rag": 4.0}},
                },
            }
        ],
    }
    module.validate_judgments(
        good,
        dataset_id="example",
        expected_queries={"a"},
        expected_approaches={"vanilla-rag"},
        expected_judges=["judge-a", "judge-b"],
    )

    empty_means = {"queries": [{"query_id": "a", "mean_by_approach": {}},
                               {"query_id": "b", "mean_by_approach": {"x": 1.0}}]}
    with pytest.raises(RuntimeError, match="example.*a"):
        module.validate_judgments(
            empty_means,
            dataset_id="example",
            expected_queries={"a", "b"},
            expected_approaches={"x"},
            expected_judges=["judge-a"],
        )

    with pytest.raises(RuntimeError, match="no queries"):
        module.validate_judgments(
            {"queries": []}, dataset_id="example", expected_queries={"a"},
            expected_approaches={"x"}, expected_judges=["judge-a"],
        )
    module.validate_judgments(
        {"status": "disabled", "judges": [], "queries": []}, dataset_id="example",
        expected_queries={"a"}, expected_approaches={"x"}, expected_judges=[],
    )

    incomplete = json.loads(json.dumps(good))
    incomplete["queries"][0]["per_judge"].pop("judge-b")
    with pytest.raises(RuntimeError, match="judge coverage"):
        module.validate_judgments(
            incomplete, dataset_id="example", expected_queries={"a"},
            expected_approaches={"vanilla-rag"}, expected_judges=["judge-a", "judge-b"],
        )


def test_ladder_validates_canonical_rows_and_summary() -> None:
    module = _load_ladder_module()
    runtime = {
        "project": "rag-showcase",
        "base_port": 22000,
        "provider_sources": {"llm": "ollama-localhost", "comfyui": "disabled"},
        "rag_showcase": {
            "commit": "repo", "tree": "repo-tree", "dirty": True,
            "patch_sha256": "repo-patch", "patch_capture": "exact",
        },
        "atlas": {
            "commit": "atlas", "tree": "atlas-tree", "dirty": False,
            "patch_sha256": "atlas-patch", "patch_capture": "exact",
        },
        "judge_panel": {
            "endpoint": "atlas-litellm", "models": ["judge-a", "judge-b"],
            "thinking": False,
        },
        "runtime_files": {
            "model_inventory": {"sha256": "models", "entries": ["vanilla-rag"]},
            "lightrag_query_profiles": {"sha256": "profiles", "entries": ["graph-rag"]},
        },
    }
    hashes = {
        "evaluation_manifest": "a", "dataset_questions": "b", "flavors": "c",
        "roles": "d", "consumer_manifest": "e", "atlas_env_user": "f",
        "runtime_model_inventory": "g", "lightrag_query_profiles": "h",
    }
    rows = [
        {"row_id": "a", "dataset": {"id": "example"}, "status": "ok",
         "question": {"id": "q1"}, "approach": {"model": "a"},
         "reproducibility": {"config_hashes": hashes, "runtime": runtime},
         "metrics": {"ragas": {"status": "ok", "requested": ["answer_relevancy"],
                                "scores": {"answer_relevancy": 0.8}}}},
        {"row_id": "b", "dataset": {"id": "example"}, "status": "error",
         "question": {"id": "q1"}, "approach": {"model": "b"},
         "reproducibility": {"config_hashes": hashes, "runtime": runtime},
         "metrics": {"ragas": {"status": "not_run", "requested": [], "scores": {}}}},
    ]
    module.validate_canonical_rows(
        rows, dataset_id="example", expected_cells=2,
        expected_queries={"q1"}, expected_approaches={"a", "b"},
        expected_ragas={"answer_relevancy"},
    )
    with pytest.raises(RuntimeError, match="duplicate row ids"):
        module.validate_canonical_rows(
            rows + [rows[0]], dataset_id="example", expected_cells=3,
            expected_queries={"q1"}, expected_approaches={"a", "b"},
            expected_ragas={"answer_relevancy"},
        )
    with pytest.raises(RuntimeError, match="expected 3.*found 2"):
        module.validate_canonical_rows(
            rows, dataset_id="example", expected_cells=3,
            expected_queries={"q1"}, expected_approaches={"a", "b"},
            expected_ragas={"answer_relevancy"},
        )

    missing_runtime = json.loads(json.dumps(rows))
    missing_runtime[0]["reproducibility"].pop("runtime")
    with pytest.raises(RuntimeError, match="runtime provenance"):
        module.validate_canonical_rows(
            missing_runtime, dataset_id="example", expected_cells=2,
            expected_queries={"q1"}, expected_approaches={"a", "b"},
            expected_ragas={"answer_relevancy"},
        )

    disabled_ragas = json.loads(json.dumps(rows))
    disabled_ragas[0]["metrics"]["ragas"] = {
        "status": "disabled", "requested": ["answer_relevancy"], "scores": {},
    }
    with pytest.raises(RuntimeError, match="Ragas.*disabled"):
        module.validate_canonical_rows(
            disabled_ragas, dataset_id="example", expected_cells=2,
            expected_queries={"q1"}, expected_approaches={"a", "b"},
            expected_ragas={"answer_relevancy"},
        )

    summary = {
        "schema_version": 1,
        "datasets": {"example": {"coverage": {
            "total_rows": 2, "ok": 1, "errors": 1, "timeouts": 0,
        }}},
    }
    module.validate_evaluation_summary(
        summary, dataset_id="example", expected_cells=2,
        expected_status_counts={"ok": 1, "errors": 1, "timeouts": 0},
    )
    with pytest.raises(RuntimeError, match="missing dataset"):
        module.validate_evaluation_summary(
            summary, dataset_id="other", expected_cells=2,
            expected_status_counts={"ok": 1, "errors": 1, "timeouts": 0},
        )
    with pytest.raises(RuntimeError, match="coverage does not match"):
        module.validate_evaluation_summary(
            summary, dataset_id="example", expected_cells=2,
            expected_status_counts={"ok": 2, "errors": 0, "timeouts": 0},
        )


def test_ladder_delegates_lightrag_drain_to_atlas() -> None:
    module = _load_ladder_module()
    assert not hasattr(module, "wait_for_lightrag")
    assert not hasattr(module, "lightrag_status")
    assert not hasattr(module, "lightrag_documents")


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


def test_flavor_tier_selects_every_non_base_alias() -> None:
    module = _load_ladder_module()

    aliases = module.flavor_tier_models()

    assert len(aliases) == 12
    assert "graph-rag-rerank" in aliases
    assert "lazy-graph-rag-wide" in aliases
    assert not set(aliases) & set(module.flavor_config.SUPPORTED_APPROACHES)


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
    monkeypatch.setenv("JUDGE_MODELS", ",".join(DEFAULT_JUDGES))
    monkeypatch.setattr(module, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(module, "DOC_RESULTS", tmp_path / "doc-results")
    monkeypatch.setattr(
        module,
        "envval",
        lambda key, default="": "backend-token"
        if key == "BACKEND_INTERNAL_API_TOKEN"
        else default,
    )
    module.RESULTS.mkdir(parents=True)
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("alpha", encoding="utf-8")

    seen_envs: list[dict] = []
    def fake_run(cmd, env=None, **kw):
        env = dict(env or {})
        seen_envs.append(env)
        if "MATRIX_RESULTS_FILE" in env:
            (module.RESULTS / env["MATRIX_RESULTS_FILE"]).write_text(json.dumps(
                {"models": ["vanilla-rag"], "queries": [{"id": "q1"}],
                 "cells": [{"query_id": "q1", "model": "vanilla-rag", "ok": True}]}),
                encoding="utf-8")
            (module.RESULTS / env["MATRIX_CANONICAL_FILE"]).write_text(
                json.dumps(_canonical_fixture(
                    env["MATRIX_DATASET_ID"], env["MATRIX_RUN_ID"] + "-q1"
                )) + "\n",
                encoding="utf-8",
            )
            (module.RESULTS / env["MATRIX_SUMMARY_FILE"]).write_text(
                json.dumps(_summary_fixture(env["MATRIX_DATASET_ID"])),
                encoding="utf-8",
            )
        elif "JUDGE_RESULTS_FILE" in env:
            (module.RESULTS / env["JUDGE_RESULTS_FILE"]).write_text(
                json.dumps(_judgments_fixture("ds")), encoding="utf-8"
            )
    monkeypatch.setattr(module, "run", fake_run)

    ingestion = {"id": "ing-1", "profile": "ds", "revision": "rev", "content_digest": "digest"}
    module.run_matrix_and_judge({"id": "ds", "queries_file": "q.json",
                                 "corpus_path": str(corpus)}, ingestion, "2026-07-04",
                                approaches="", flavors="")
    matrix_env = seen_envs[0]
    assert matrix_env["MATRIX_QUERIES_FILE"] == "q.json"
    assert matrix_env["MATRIX_DATASET_ID"] == "ds"
    assert matrix_env["MATRIX_RUN_ID"] == "live-2026-07-04-ds"
    assert matrix_env["MATRIX_CANONICAL_FILE"].endswith("-evidence.jsonl")
    assert matrix_env["MATRIX_SUMMARY_FILE"].endswith("-evaluation.json")
    assert matrix_env["MATRIX_INGESTION_ID"] == "ing-1"
    assert matrix_env["MATRIX_INGESTION_JOB_ID"] == "ing-1"
    assert matrix_env["MATRIX_INGESTION_PROFILE"] == "ds"
    assert matrix_env["MATRIX_INGESTION_REVISION"] == "rev"
    assert matrix_env["MATRIX_INGESTION_CONTENT_DIGEST"] == "digest"
    assert matrix_env["MATRIX_INGESTION_MODE"] == "atlas-job"
    assert matrix_env["MATRIX_EVALUATOR_API_KEY_HEADER"] == "Authorization"
    assert matrix_env["MATRIX_EVALUATOR_API_KEY"] == "Bearer backend-token"
    assert "MATRIX_MODELS" not in matrix_env
    assert "MATRIX_FLAVORS" not in matrix_env

    # The validated flags must still reach the subprocess (the scrub above must
    # not eat them).
    module.run_matrix_and_judge({"id": "ds2", "queries_file": "q.json",
                                 "corpus_path": str(corpus)}, ingestion, "2026-07-04",
                                approaches="vanilla-rag", flavors="graph-rag-wide")
    matrix_env = seen_envs[3]
    assert matrix_env["MATRIX_MODELS"] == "vanilla-rag"
    assert matrix_env["MATRIX_FLAVORS"] == "graph-rag-wide"

    module.run_matrix_and_judge(
        {"id": "ds3", "queries_file": "q.json", "corpus_path": str(corpus)},
        ingestion,
        "2026-07-04",
        approaches="graph-rag-rerank",
        flavors="",
        artifact_tier="flavors",
    )
    matrix_env = seen_envs[6]
    assert matrix_env["MATRIX_RUN_ID"] == "live-2026-07-04-ds3-flavors"
    assert matrix_env["MATRIX_RESULTS_FILE"] == "live-2026-07-04-ds3-flavors-matrix.json"
    assert matrix_env["MATRIX_CANONICAL_FILE"] == "live-2026-07-04-ds3-flavors-evidence.jsonl"


def test_snapshot_manifest_keeps_base_and_flavor_tiers_separate(monkeypatch, tmp_path) -> None:
    module = _load_ladder_module()
    manifest = {"datasets": [{"id": "ds", "status": "measured"}]}
    written = []
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setattr(module, "load_manifest", lambda: manifest)
    monkeypatch.setattr(module, "write_manifest", lambda value: written.append(value))
    base = [tmp_path / f"base-{kind}" for kind in ("matrix", "judgments", "evidence", "evaluation")]
    flavor = [tmp_path / f"flavor-{kind}" for kind in ("matrix", "judgments", "evidence", "evaluation")]

    module.update_dataset_snapshots("ds", *base, flavor_paths=tuple(flavor))

    row = written[0]["datasets"][0]
    assert row["matrix_snapshot"] == "base-matrix"
    assert row["flavor_matrix_snapshot"] == "flavor-matrix"
    assert row["flavor_evaluation_snapshot"] == "flavor-evaluation"


def test_cold_ingestion_discards_stale_working_evidence_before_matrix(
        monkeypatch, tmp_path) -> None:
    module = _load_ladder_module()
    monkeypatch.setenv("JUDGE_MODELS", ",".join(DEFAULT_JUDGES))
    monkeypatch.setattr(module, "RESULTS", tmp_path / "results")
    monkeypatch.setattr(module, "DOC_RESULTS", tmp_path / "doc-results")
    monkeypatch.setattr(
        module,
        "envval",
        lambda key, default="": "backend-token"
        if key == "BACKEND_INTERNAL_API_TOKEN"
        else default,
    )
    module.RESULTS.mkdir(parents=True)
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "doc.md").write_text("alpha", encoding="utf-8")
    dataset = {"id": "ds", "queries_file": "q.json", "corpus_path": str(corpus)}
    date_stamp = "2026-07-04"
    stale = module.RESULTS / f"live-{date_stamp}-ds-evidence.jsonl"
    stale.write_text('{"row_id":"stale"}\n', encoding="utf-8")

    seen_matrix_env: dict[str, str] = {}

    def fake_run(cmd, env=None, **kw):
        env = dict(env or {})
        if "MATRIX_RESULTS_FILE" in env:
            assert not stale.exists()
            seen_matrix_env.update(env)
            (module.RESULTS / env["MATRIX_RESULTS_FILE"]).write_text(json.dumps(
                {"models": ["vanilla-rag"], "queries": [{"id": "q1"}],
                 "cells": [{"query_id": "q1", "model": "vanilla-rag", "ok": True}]}),
                encoding="utf-8",
            )
            (module.RESULTS / env["MATRIX_CANONICAL_FILE"]).write_text(
                json.dumps(_canonical_fixture("ds", "new")) + "\n", encoding="utf-8"
            )
            (module.RESULTS / env["MATRIX_SUMMARY_FILE"]).write_text(
                json.dumps(_summary_fixture("ds")), encoding="utf-8"
            )
        elif "JUDGE_RESULTS_FILE" in env:
            (module.RESULTS / env["JUDGE_RESULTS_FILE"]).write_text(
                json.dumps(_judgments_fixture("ds")), encoding="utf-8"
            )

    monkeypatch.setattr(module, "run", fake_run)
    ingestion = {
        "id": "job-1",
        "profile": "ds",
        "revision": "rev-1",
        "content_digest": "digest-1",
    }
    module.run_matrix_and_judge(
        dataset, ingestion, date_stamp, approaches="vanilla-rag", flavors="",
        fresh_ingestion=True,
    )

    assert seen_matrix_env["MATRIX_INGESTION_REVISION"] == "rev-1"
    assert seen_matrix_env["MATRIX_INGESTION_JOB_ID"] == "job-1"


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
