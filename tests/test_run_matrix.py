"""Unit tests for the matrix harness's env plumbing and per-cell error contract."""
from __future__ import annotations

import json

import httpx
import pytest
import respx

import compare.run_matrix as run_matrix


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
    monkeypatch.setenv("MATRIX_CANONICAL_FILE", str(canonical))
    monkeypatch.setenv("MATRIX_RUN_ID", "test-failure-run")
    monkeypatch.setenv("MATRIX_MODELS", "vanilla-rag,hybrid-rag")

    def responder(request):
        body = json.loads(request.content)
        if body["model"] == "vanilla-rag":
            raise httpx.ConnectError("backend down")
        return httpx.Response(200, json={
            "choices": [{"message": {"content": "fine answer\n\n---\n📊 1.0s · 1 chunk · 2 LLM calls · 0 cloud"}}]})
    respx.post("http://localhost:9/v1/chat/completions").mock(side_effect=responder)

    run_matrix.main()

    out = json.loads(results.read_text(encoding="utf-8"))
    cells = {c["model"]: c for c in out["cells"]}
    assert cells["vanilla-rag"]["ok"] is False
    assert "ConnectError" in cells["vanilla-rag"]["error"]
    assert cells["hybrid-rag"]["ok"] is True
    assert cells["hybrid-rag"]["metrics"] == {"seconds": 1.0, "chunks": 1,
                                              "llm_calls": 2, "cloud_calls": 0}
    assert out["models"] == ["vanilla-rag", "hybrid-rag"]
    rows = [json.loads(line) for line in canonical.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    assert {row["status"] for row in rows} == {"error", "ok"}
    successful = next(row for row in rows if row["status"] == "ok")
    assert successful["metrics"]["ragas"]["status"] == "not_evaluable"
    assert out["canonical_rows_file"] == str(canonical)


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
