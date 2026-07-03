from pathlib import Path

import compare.run_matrix as run_matrix
import compare.judge as judge


def test_run_matrix_uses_env_selected_query_and_result_files(monkeypatch) -> None:
    monkeypatch.setenv("MATRIX_QUERIES_FILE", "demo/graph_native_queries.yaml")
    monkeypatch.setenv("MATRIX_RESULTS_FILE", "graph_native_matrix.json")

    assert run_matrix.queries_file() == Path("demo/graph_native_queries.yaml")
    assert run_matrix.results_file() == run_matrix.RESULTS / "graph_native_matrix.json"


def test_run_matrix_expands_matrix_flavors(monkeypatch, tmp_path) -> None:
    f = tmp_path / "flavors.yaml"
    f.write_text(
        """
flavors:
  - alias: graph-rag-wide
    base: graph-rag
    flavor: wide
""",
        encoding="utf-8",
    )
    monkeypatch.delenv("MATRIX_MODELS", raising=False)
    monkeypatch.setenv("MATRIX_FLAVORS_FILE", str(f))
    monkeypatch.setenv("MATRIX_FLAVORS", "default,graph-rag-wide")

    profiles = run_matrix.selected_profiles()

    assert [p.alias for p in profiles[:6]] == run_matrix.ALL_MODELS
    assert profiles[-1].alias == "graph-rag-wide"
    assert profiles[-1].base == "graph-rag"


def test_run_matrix_model_override_preserves_explicit_model_list(monkeypatch) -> None:
    monkeypatch.setenv("MATRIX_MODELS", "graph-rag-wide,hybrid-rag")
    monkeypatch.delenv("MATRIX_FLAVORS", raising=False)

    profiles = run_matrix.selected_profiles()

    assert [p.alias for p in profiles] == ["graph-rag-wide", "hybrid-rag"]
    assert [p.base for p in profiles] == ["graph-rag", "hybrid-rag"]


def test_judge_uses_env_selected_input_and_result_files(monkeypatch) -> None:
    monkeypatch.setenv("JUDGE_MATRIX_FILE", "graph_native_matrix.json")
    monkeypatch.setenv("JUDGE_RESULTS_FILE", "graph_native_judgments.json")

    assert judge.matrix_file() == judge.RESULTS / "graph_native_matrix.json"
    assert judge.judgments_file() == judge.RESULTS / "graph_native_judgments.json"
