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
    monkeypatch.setattr(run_matrix, "envval",
                        lambda key, default="": {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k"}[key])
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
    monkeypatch.setattr(run_matrix, "envval",
                        lambda key, default="": {"LITELLM_PORT": "9", "LITELLM_MASTER_KEY": "k"}[key])
    monkeypatch.setenv("MATRIX_QUERIES_FILE", str(queries))
    monkeypatch.setenv("MATRIX_RESULTS_FILE", str(results))
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
