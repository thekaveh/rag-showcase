"""Unit tests for the matrix harness's env plumbing and per-cell error contract."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

import compare.run_matrix as run_matrix


def _stub_runtime_provenance(monkeypatch) -> None:
    monkeypatch.setattr(
        run_matrix,
        "_runtime_provenance",
        lambda manifest=None: {
            "project": "rag-showcase",
            "runtime_files": {
                "model_inventory": {"sha256": "models", "entries": ["vanilla-rag"]},
                "lightrag_query_profiles": {
                    "sha256": "profiles",
                    "entries": ["graph-rag"],
                },
            },
        },
    )


def test_git_state_records_commit_tree_and_deterministic_patch_digest() -> None:
    state = run_matrix._git_state(run_matrix.ROOT)

    assert len(str(state["commit"])) == 40
    assert len(str(state["tree"])) == 40
    assert isinstance(state["dirty"], bool)
    assert len(str(state["patch_sha256"])) == 64
    assert state["patch_sha256"] == run_matrix._git_state(run_matrix.ROOT)["patch_sha256"]


def test_runtime_provenance_binds_repo_atlas_provider_and_generated_registries(
    monkeypatch,
) -> None:
    monkeypatch.setenv("JUDGE_MODELS", "judge-a,judge-b")
    values = {
        "PROJECT_NAME": "rag-showcase",
        "BASE_PORT": "22000",
        "LLM_PROVIDER_SOURCE": "ollama-localhost",
        "COMFYUI_SOURCE": "disabled",
    }
    monkeypatch.setattr(
        run_matrix, "envval", lambda key, default="": values.get(key, default)
    )
    monkeypatch.setattr(
        run_matrix,
        "_git_state",
        lambda path: {
            "commit": "repo-sha" if path == run_matrix.ROOT else "atlas-sha",
            "dirty": True,
        },
    )
    monkeypatch.setattr(
        run_matrix,
        "_runtime_file",
        lambda path, kind: {
            "path": str(path),
            "sha256": f"{kind}-digest",
            "entries": ["vanilla-rag"] if kind == "models" else ["graph-rag-rerank"],
        },
    )

    runtime = run_matrix._runtime_provenance()

    assert runtime["project"] == "rag-showcase"
    assert runtime["base_port"] == 22000
    assert runtime["provider_sources"] == {
        "llm": "ollama-localhost",
        "comfyui": "disabled",
    }
    assert runtime["rag_showcase"] == {"commit": "repo-sha", "dirty": True}
    assert runtime["atlas"] == {"commit": "atlas-sha", "dirty": True}
    assert runtime["runtime_files"]["model_inventory"]["sha256"]
    assert "vanilla-rag" in runtime["runtime_files"]["model_inventory"]["entries"]
    assert runtime["runtime_files"]["lightrag_query_profiles"]["sha256"]
    assert "graph-rag-rerank" in runtime["runtime_files"]["lightrag_query_profiles"]["entries"]


def test_legacy_cell_converts_latency_ms_to_seconds() -> None:
    # latency_ms is a harness-measured millisecond duration; the legacy cell
    # exposes it as latency_s (seconds, 1 decimal) for older report consumers.
    # A wrong divisor here silently corrupts every displayed latency by a
    # constant factor with no test catching it.
    row = {
        "question": {"id": "q1"},
        "approach": {
            "model": "vanilla-rag", "base_model": "vanilla-rag",
            "flavor": "default", "requires_reingest": False,
        },
        "status": "error",
        "metrics": {"operational": {"latency_ms": 4321, "attempts": 1}},
        "evidence": {},
        "error": {"type": "TimeoutError", "message": "boom"},
    }

    cell = run_matrix._legacy_cell(row)

    assert cell["latency_s"] == 4.3


def _stub_provenance_deps(monkeypatch) -> None:
    # Same mock shape as test_runtime_provenance_binds_repo_atlas_provider_and_
    # generated_registries, factored out so JUDGE_THINK tests can reach the full
    # return path (real _runtime_file/_git_state need infra/ artifacts this bare
    # test env doesn't have).
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": default)
    monkeypatch.setattr(run_matrix, "_git_state", lambda path: {"commit": "x", "dirty": False})
    monkeypatch.setattr(
        run_matrix, "_runtime_file",
        lambda path, kind: {"path": str(path), "sha256": "x", "entries": []},
    )


@pytest.mark.parametrize("raw, expected", [("true", True), ("false", False), ("omit", None)])
def test_runtime_provenance_normalizes_judge_think(monkeypatch, raw, expected) -> None:
    # compare/judge.py already parses JUDGE_THINK the same way and is tested for
    # it — this is a second, independent implementation feeding the committed
    # run-provenance record, and had no test of its own at all.
    monkeypatch.setenv("JUDGE_MODELS", "judge-a")
    monkeypatch.setenv("JUDGE_THINK", raw)
    _stub_provenance_deps(monkeypatch)

    runtime = run_matrix._runtime_provenance()

    assert runtime["judge_panel"]["thinking"] == expected


def test_runtime_provenance_rejects_invalid_judge_think(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_MODELS", "judge-a")
    monkeypatch.setenv("JUDGE_THINK", "maybe")
    _stub_provenance_deps(monkeypatch)

    with pytest.raises(ValueError, match="JUDGE_THINK must be true, false, or omit"):
        run_matrix._runtime_provenance()


def test_runtime_file_rejects_non_object_model_list_rows(tmp_path) -> None:
    path = tmp_path / "consumer-models.yaml"
    path.write_text("model_list:\n  - model_name: ok\n  - not-an-object\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="expected a list of models entry objects"):
        run_matrix._runtime_file(path, kind="models")


def test_runtime_file_rejects_non_list_profiles(tmp_path) -> None:
    path = tmp_path / "lightrag-query-profiles.json"
    path.write_text(json.dumps({"profiles": {"not": "a list"}}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="expected a list of profiles entry objects"):
        run_matrix._runtime_file(path, kind="profiles")


def test_dataset_for_raises_on_ambiguous_shared_queries_file(tmp_path, monkeypatch) -> None:
    # Two configured datasets sharing the same queries_file must not silently fall
    # through to the "ad hoc dataset" branch — that would mislabel provenance for
    # a real manifest-authoring error instead of surfacing it.
    from compare.evaluation import load_manifest

    (tmp_path / "questions").mkdir()
    (tmp_path / "corpus" / "a").mkdir(parents=True)
    (tmp_path / "corpus" / "b").mkdir(parents=True)
    shared = tmp_path / "questions" / "shared.yaml"
    shared.write_text("queries: []\n", encoding="utf-8")
    (tmp_path / "datasets.yaml").write_text(
        """
datasets:
  - id: ds-a
    label: Dataset A
    complexity_level: 1
    status: measured
    corpus_path: corpus/a
    queries_file: questions/shared.yaml
    graph_nature: relational
  - id: ds-b
    label: Dataset B
    complexity_level: 1
    status: measured
    corpus_path: corpus/b
    queries_file: questions/shared.yaml
    graph_nature: relational
""",
        encoding="utf-8",
    )
    manifest_path = tmp_path / "evaluation.yaml"
    manifest_path.write_text(
        """
version: 1
datasets_file: datasets.yaml
approaches:
  - model: vanilla-rag
    evidence: answer_with_contexts
metrics:
  ragas: []
  judge_panel:
    enabled: false
    models: []
run:
  retries: 0
  timeout_s: 10
  evaluator_timeout_s: 20
  concurrency: 1
  seed: test-seed
""",
        encoding="utf-8",
    )
    manifest = load_manifest(manifest_path)
    monkeypatch.delenv("MATRIX_DATASET_ID", raising=False)

    with pytest.raises(ValueError, match="ambiguous.*ds-a.*ds-b"):
        run_matrix._dataset_for(manifest, shared)


def test_runtime_provenance_requires_judges_for_enabled_panel(monkeypatch) -> None:
    monkeypatch.delenv("JUDGE_MODELS", raising=False)

    with pytest.raises(ValueError, match="JUDGE_MODELS"):
        run_matrix._runtime_provenance()


def test_envval_last_assignment_wins_and_default(tmp_path, monkeypatch) -> None:
    env = tmp_path / "infra" / ".env"
    env.parent.mkdir()
    env.write_text("LITELLM_PORT=1111\nOTHER=x\nLITELLM_PORT=2222\n", encoding="utf-8")
    monkeypatch.setattr(run_matrix, "ROOT", tmp_path)
    assert run_matrix.envval("LITELLM_PORT") == "2222"   # Atlas appends duplicates
    assert run_matrix.envval("MISSING") == ""
    assert run_matrix.envval("MISSING", "fallback") == "fallback"
    monkeypatch.setattr(run_matrix, "ROOT", tmp_path / "nowhere")
    assert run_matrix.envval("LITELLM_PORT", "dflt") == "dflt"  # no .env at all


def test_selected_profiles_defaults_to_all_six(monkeypatch) -> None:
    monkeypatch.delenv("MATRIX_MODELS", raising=False)
    monkeypatch.delenv("MATRIX_FLAVORS", raising=False)
    monkeypatch.delenv("MATRIX_FLAVORS_FILE", raising=False)
    profiles = run_matrix.selected_profiles()
    assert [p.alias for p in profiles][:6] == run_matrix.ALL_MODELS
    assert len(profiles) == 6  # canonical six only, no flavors without a selection


def test_main_fails_fast_without_gateway_config(monkeypatch) -> None:
    # Without LITELLM_PORT/MASTER_KEY the old behavior ran the whole matrix against
    # "http://localhost:" and exited 0 with a 100%-error file.
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": "")
    with pytest.raises(SystemExit, match="LITELLM_PORT"):
        run_matrix.main()


def test_main_rejects_malformed_query_rows_before_running(tmp_path, monkeypatch) -> None:
    queries = tmp_path / "queries.yaml"
    queries.write_text("- id: q1\n  query: ok\n- query: missing id\n", encoding="utf-8")
    values = {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k", "BACKEND_PORT": "8"}
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": values.get(key, default))
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))
    with pytest.raises(SystemExit, match="missing id/query"):
        run_matrix.main()


def test_main_rejects_duplicate_query_ids_before_running(tmp_path, monkeypatch) -> None:
    queries = tmp_path / "queries.yaml"
    queries.write_text(
        "- id: same\n  query: first\n- id: same\n  query: second\n",
        encoding="utf-8",
    )
    values = {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k", "BACKEND_PORT": "8"}
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": values.get(key, default))
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))

    with pytest.raises(SystemExit, match="duplicate query id.*same"):
        run_matrix.main()


@respx.mock
def test_main_records_failed_cell_and_completes(tmp_path, monkeypatch) -> None:
    # The per-cell contract the dataset ladder depends on: one failed approach is
    # recorded as ok:False with the error string; the run continues and writes.
    queries = tmp_path / "queries.yaml"
    queries.write_text("- id: q1\n  query: what is alpha?\n", encoding="utf-8")
    results = tmp_path / "matrix.json"
    values = {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k", "BACKEND_PORT": "8"}
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": values.get(key, default))
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))
    monkeypatch.setenv("MATRIX_RESULTS_FILE", str(results))
    canonical = tmp_path / "matrix.jsonl"
    summary = tmp_path / "summary.json"
    monkeypatch.setenv("MATRIX_CANONICAL_FILE", str(canonical))
    monkeypatch.setenv("MATRIX_SUMMARY_FILE", str(summary))
    monkeypatch.setenv("MATRIX_RUN_ID", "test-failure-run")
    monkeypatch.setenv("MATRIX_MODELS", "vanilla-rag,hybrid-rag")
    monkeypatch.setenv("MATRIX_INGESTION_ID", "ing-1")
    monkeypatch.setenv("MATRIX_INGESTION_PROFILE", "baseline_curated")
    monkeypatch.setenv("MATRIX_INGESTION_REVISION", "rev-1")
    monkeypatch.setenv("MATRIX_INGESTION_CONTENT_DIGEST", "digest-1")
    monkeypatch.setenv("JUDGE_MODELS", "judge-a,judge-b")
    _stub_runtime_provenance(monkeypatch)

    def responder(request):
        body = json.loads(request.content)
        assert body["cache"] == {"no-cache": True, "no-store": True}
        if body["model"] == "vanilla-rag":
            raise httpx.ConnectError("backend down")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "fine answer\n\n---\n📊 1.0s · 1 chunk · 2 LLM calls · 0 cloud"}}],
            "rag_showcase": {
                "schema_version": 1,
                "sources": [],
                "metrics": {
                    "seconds": 1.0,
                    "chunks": 1,
                    "llm_calls": 2,
                    "cloud_calls": 0,
                },
                "lazy_graph": {"cache_hit": True},
            },
        })
    respx.post("http://localhost:9/v1/chat/completions").mock(side_effect=responder)
    respx.post("http://localhost:8/api/rag/evaluate").mock(
        return_value=httpx.Response(503, text="evaluator unavailable")
    )

    run_matrix.main()

    out = json.loads(results.read_text(encoding="utf-8"))
    cells = {c["model"]: c for c in out["cells"]}
    assert cells["vanilla-rag"]["ok"] is False
    assert "ConnectError" in cells["vanilla-rag"]["error"]
    assert cells["hybrid-rag"]["ok"] is True
    assert cells["hybrid-rag"]["metrics"] == {"seconds": 1.0, "chunks": 1,
                                              "llm_calls": 2, "cloud_calls": 0}
    assert cells["hybrid-rag"]["approach_metadata"] == {
        "lazy_graph": {"cache_hit": True}
    }
    assert out["models"] == ["vanilla-rag", "hybrid-rag"]
    assert out["ingestion"] == {
        "id": "ing-1",
        "job_id": "ing-1",
        "profile": "baseline_curated",
        "revision": "rev-1",
        "content_digest": "digest-1",
        "mode": "showcase-managed",
    }
    rows = [json.loads(line) for line in canonical.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert {row["status"] for row in rows} == {"error", "ok"}
    successful = next(row for row in rows if row["status"] == "ok")
    ragas = successful["metrics"]["ragas"]
    assert ragas["status"] == "error"
    assert ragas["not_evaluable"] == {"faithfulness": "retrieved_contexts_required"}
    assert "HTTPStatusError" in ragas["error"]
    assert out["canonical_rows_file"] == str(canonical)
    assert out["evaluation_summary_file"] == str(summary)
    summary_payload = json.loads(summary.read_text(encoding="utf-8"))
    assert summary_payload["datasets"]["queries"]["coverage"]["total_rows"] == 2
    assert rows[0]["reproducibility"]["ingestion"] == out["ingestion"]


def test_parse_content_nested_wrapper_payload_uses_outer_footer() -> None:
    # n8n-adaptive-rag passes the routed approach's fully rendered payload through
    # as its answer, nesting a second footer + sources block. Metrics must be the
    # WRAPPER's (last footer), the answer must truncate before the nested
    # rendering, and both source blocks must be captured.
    inner = ("the routed answer"
             "\n\n<details><summary>🔎 Retrieved context (1 source)</summary>\n"
             "\n**1. Inner Doc** · score 0.500\n\n> snippet\n\n</details>"
             "\n\n---\n📊 2.0s · 5 chunks · 2 LLM calls · 0 cloud")
    outer = (inner
             + "\n\n<details><summary>🔎 Retrieved context (1 source)</summary>\n"
             "\n**1. 🧭 Adaptive route**\n\n> n8n routed this query as **complex**.\n\n</details>"
             + "\n\n---\n📊 6.5s · 0 chunks · 1 LLM call · 0 cloud")

    parsed = run_matrix.parse_content(outer)

    assert parsed["metrics"] == {"seconds": 6.5, "chunks": 0,
                                 "llm_calls": 1, "cloud_calls": 0}  # wrapper's, not inner
    assert parsed["answer"] == "the routed answer"
    titles = [s["title"] for s in parsed["sources"]]
    assert "Inner Doc" in titles and "🧭 Adaptive route" in titles


def test_main_rejects_empty_queries_file(tmp_path, monkeypatch) -> None:
    # An empty (or all-comments) YAML loads as None; the run must exit with a
    # clean message, not a TypeError from iterating None.
    queries = tmp_path / "queries.yaml"
    queries.write_text("# no rows here\n", encoding="utf-8")
    values = {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k", "BACKEND_PORT": "8"}
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": values.get(key, default))
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))
    with pytest.raises(SystemExit, match="no query rows"):
        run_matrix.main()


@respx.mock
def test_main_routes_structured_evidence_to_atlas_evaluator(tmp_path, monkeypatch) -> None:
    queries = tmp_path / "queries.yaml"
    queries.write_text("- id: q1\n  query: grounded question\n", encoding="utf-8")
    results = tmp_path / "matrix.json"
    canonical = tmp_path / "evidence.jsonl"
    values = {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k", "BACKEND_PORT": "8"}
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": values.get(key, default))
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))
    monkeypatch.setenv("MATRIX_RESULTS_FILE", str(results))
    monkeypatch.setenv("MATRIX_CANONICAL_FILE", str(canonical))
    monkeypatch.setenv("MATRIX_RUN_ID", "atlas-eval-run")
    monkeypatch.setenv("MATRIX_MODELS", "vanilla-rag")
    monkeypatch.setenv("JUDGE_MODELS", "judge-a,judge-b")
    _stub_runtime_provenance(monkeypatch)

    respx.post("http://localhost:9/v1/chat/completions").mock(return_value=httpx.Response(
        200,
        json={
            "id": "completion-1",
            "model": "vanilla-rag",
            "choices": [{"message": {"content": "grounded answer"}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3},
            "rag_showcase": {
                "schema_version": 1,
                "sources": [{"title": "Doc", "snippet": "source context", "score": 0.9}],
                "metrics": {"seconds": 1.0, "chunks": 1, "llm_calls": 2, "cloud_calls": 0},
            },
        },
    ))
    evaluator = respx.post("http://localhost:8/api/rag/evaluate").mock(
        return_value=httpx.Response(200, json={
            "metrics": ["faithfulness", "answer_relevancy"],
            "record_count": 1,
            "evaluator_model": "eval-model",
            "embeddings_model": "embed-model",
            "results": [{
                "record_index": 0,
                "scores": {"faithfulness": 0.8, "answer_relevancy": 0.7},
                "metadata": {},
            }],
            "metadata": {"runner": "ragas"},
        })
    )

    run_matrix.main()

    assert evaluator.called
    row = json.loads(canonical.read_text(encoding="utf-8"))
    assert row["metrics"]["ragas"]["status"] == "ok"
    assert row["metrics"]["ragas"]["scores"] == {
        "answer_relevancy": 0.7,
        "faithfulness": 0.8,
    }
    assert row["metrics"]["ragas"]["evaluator_model"] == "eval-model"


@respx.mock
def test_main_resume_does_not_repeat_completed_gateway_call(tmp_path, monkeypatch) -> None:
    queries = tmp_path / "queries.yaml"
    queries.write_text("- id: q1\n  query: resume me\n", encoding="utf-8")
    results = tmp_path / "matrix.json"
    canonical = tmp_path / "evidence.jsonl"
    values = {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k", "BACKEND_PORT": "8"}
    monkeypatch.setattr(run_matrix, "envval", lambda key, default="": values.get(key, default))
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))
    monkeypatch.setenv("MATRIX_RESULTS_FILE", str(results))
    monkeypatch.setenv("MATRIX_CANONICAL_FILE", str(canonical))
    monkeypatch.setenv("MATRIX_RUN_ID", "resume-run")
    monkeypatch.setenv("MATRIX_MODELS", "vanilla-rag")
    monkeypatch.setenv("JUDGE_MODELS", "judge-a,judge-b")
    _stub_runtime_provenance(monkeypatch)
    route = respx.post("http://localhost:9/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "id": "completion-1",
            "model": "vanilla-rag",
            "choices": [{"message": {"content": "answer"}}],
            "usage": {},
        })
    )

    run_matrix.main()
    run_matrix.main()

    assert route.call_count == 1
    assert len(canonical.read_text(encoding="utf-8").splitlines()) == 1
