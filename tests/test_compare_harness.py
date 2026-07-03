from pathlib import Path

import pytest

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


@pytest.mark.parametrize("chunks,calls", [(5, 2), (1, 1)])
def test_parse_content_round_trips_build_response(chunks, calls) -> None:
    # run_matrix.parse_content re-parses the backend's rendered answer/sources/metrics
    # with regexes that mirror openai_io._render_footer/_render_sources across the
    # process boundary (the host harness only ever sees rendered text over HTTP, it
    # cannot import the container module). Guard the two against silent drift: a change
    # to either the renderer or the parser must keep this round-trip green. The (1, 1)
    # case covers the singular "1 chunk"/"1 LLM call" -> `s?` regex coupling.
    from rag.common.openai_io import Metrics, Source, build_response

    payload = build_response(
        "hybrid-rag",
        "The answer text.",
        [Source("Doc A", "snippet a", 0.512), Source("Doc B", "snippet b", None)],
        Metrics(seconds=1.2, chunks=chunks, llm_calls=calls, cloud_calls=0),
    )
    content = payload["choices"][0]["message"]["content"]

    parsed = run_matrix.parse_content(content)

    assert parsed["answer"] == "The answer text."
    assert parsed["metrics"] == {
        "seconds": 1.2, "chunks": chunks, "llm_calls": calls, "cloud_calls": 0,
    }
    assert [s["title"] for s in parsed["sources"]] == ["Doc A", "Doc B"]
    assert parsed["sources"][0]["score"] == 0.512
    assert parsed["sources"][1]["score"] is None
