import sys
import types
from pathlib import Path

import yaml

from scripts import eval_preflight as ep

ROOT = Path(__file__).resolve().parents[1]


def test_expected_aliases_match_consumer_manifest() -> None:
    # The preflight's LiteLLM alias-completeness check must use the same set
    # Atlas compiles into /v1/models — the consumer manifest's litellm_models.
    manifest = yaml.safe_load((ROOT / "atlas.consumer.yml").read_text(encoding="utf-8"))
    declared = sorted(row["name"] for row in manifest["litellm_models"]["models"])

    assert ep.load_expected_aliases() == declared
    assert len(declared) == 19


def test_probe_source_compiles() -> None:
    compile(ep.PROBE_SOURCE, "<probe>", "exec")


def test_probe_covers_every_declared_plugin_endpoint() -> None:
    # Drive the probe from plugin.yml: every HTTP endpoint the RAG plugin
    # declares as a dependency must be probed, so adding a new dependency there
    # forces a matching probe here.
    plugin = yaml.safe_load(
        (ROOT / "backend_plugins" / "rag" / "plugin.yml").read_text(encoding="utf-8")
    )
    endpoint_vars = {
        entry["name"]
        for entry in plugin.get("env", [])
        if str(entry.get("default", "")).startswith("http")
    }
    # Sanity: plugin.yml really declares the eval's service endpoints.
    assert {
        "LITELLM_BASE_URL",
        "WEAVIATE_URL",
        "TEI_RERANKER_ENDPOINT",
        "LIGHTRAG_ENDPOINT",
        "N8N_ADAPTIVE_WEBHOOK_URL",
    } <= endpoint_vars

    for var in endpoint_vars:
        assert var in ep.PROBE_SOURCE, f"{var} declared in plugin.yml but not probed"


def test_probe_is_read_only() -> None:
    # A preflight must never mutate state or trigger a generation/eval: GET only.
    assert "httpx.get" in ep.PROBE_SOURCE
    assert "httpx.post" not in ep.PROBE_SOURCE
    assert ".embed(" not in ep.PROBE_SOURCE
    assert ".chat(" not in ep.PROBE_SOURCE
    assert "/api/pull" not in ep.PROBE_SOURCE  # never trigger an Ollama download


def test_expected_models_from_env_user() -> None:
    # The Ollama model-presence check must use the eval's real required models —
    # the *_MODEL role vars in the consumer env file.
    models = ep.load_expected_models()
    assert set(models) == {"nomic-embed-text", "mistral-small3.2:24b", "qwen3.6:latest"}


def test_probe_checks_ollama_models() -> None:
    assert "ollama" in ep.DECLARED_SERVICES
    assert "OLLAMA_ENDPOINT" in ep.PROBE_SOURCE
    assert "/api/tags" in ep.PROBE_SOURCE
    assert "EXPECTED_MODELS" in ep.PROBE_SOURCE


def test_resolve_ollama_endpoint(tmp_path: Path) -> None:
    # OLLAMA_ENDPOINT is not written to infra/.env; the endpoint is derived from
    # the active provider source (validated live in Phase 5).
    env = tmp_path / ".env"

    env.write_text("LLM_PROVIDER_SOURCE=ollama-localhost\nOLLAMA_LOCALHOST_PORT=11434\n", "utf-8")
    assert ep.resolve_ollama_endpoint(env) == "http://host.docker.internal:11434"

    env.write_text("LLM_PROVIDER_SOURCE=ollama-container-gpu\n", "utf-8")
    assert ep.resolve_ollama_endpoint(env) == "http://ollama:11434"

    env.write_text("LLM_PROVIDER_SOURCE=none\n", "utf-8")
    assert ep.resolve_ollama_endpoint(env) == ""

    # An explicit OLLAMA_ENDPOINT (should Atlas ever write one) wins.
    env.write_text("OLLAMA_ENDPOINT=http://x:11434\nLLM_PROVIDER_SOURCE=ollama-localhost\n", "utf-8")
    assert ep.resolve_ollama_endpoint(env) == "http://x:11434"


def test_probe_checks_the_ingested_weaviate_collections() -> None:
    assert "RAG_BASE_COLLECTION" in ep.PROBE_SOURCE
    assert "RAG_CONTEXTUAL_COLLECTION" in ep.PROBE_SOURCE


def test_envval_reads_last_assignment(tmp_path: Path) -> None:
    env = tmp_path / ".env"
    env.write_text("PROJECT_NAME=old\nOTHER=x\nPROJECT_NAME=rag-showcase\n", encoding="utf-8")
    assert ep.envval("PROJECT_NAME", env_path=env) == "rag-showcase"
    assert ep.envval("MISSING", env_path=env) is None


def test_overall_ok_requires_config_and_every_probe() -> None:
    green = {s: {"ok": True, "detail": ""} for s in ep.DECLARED_SERVICES}
    assert ep.overall_ok({"ok": True, "detail": ""}, green) is True
    assert ep.overall_ok(None, green) is True  # --skip-doctor
    assert ep.overall_ok({"ok": False, "detail": ""}, green) is False

    one_bad = dict(green, weaviate={"ok": False, "detail": "collection absent"})
    assert ep.overall_ok({"ok": True, "detail": ""}, one_bad) is False
    assert ep.overall_ok({"ok": True, "detail": ""}, {}) is False


def test_format_report_marks_pass_and_fail() -> None:
    probes = {s: {"ok": True, "detail": "ok"} for s in ep.DECLARED_SERVICES}
    probes["lightrag"] = {"ok": False, "detail": "ConnectError"}
    report = ep.format_report({"ok": True, "detail": "passed"}, probes)

    assert "atlas doctor" in report
    for service in ep.DECLARED_SERVICES:
        assert service in report
    assert "✓" in report and "✗" in report
    assert "FAILED" in report  # one probe failed → overall failed


def test_make_eval_check_target_runs_the_preflight() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "eval-check:" in makefile
    assert "scripts.eval_preflight" in makefile or "scripts/eval_preflight.py" in makefile


def test_graph_aliases_declared_reads_manifest(tmp_path: Path) -> None:
    # The real manifest declares graph-rag / lazy-graph-rag / agentic-rag, so an
    # empty knowledge graph must gate the eval.
    assert ep.graph_aliases_declared() is True

    # A vector-only manifest → an unpopulated graph is expected, not a failure.
    vector_only = tmp_path / "manifest.yml"
    vector_only.write_text(
        "litellm_models:\n"
        "  models:\n"
        "    - name: vanilla-rag\n"
        "      model_info: {base_approach: vanilla-rag}\n"
        "    - name: hybrid-rag\n"
        "      model_info: {base_approach: hybrid-rag}\n",
        encoding="utf-8",
    )
    assert ep.graph_aliases_declared(vector_only) is False


def test_probe_checks_graph_population() -> None:
    # The lightrag probe must go beyond /health to the read-only /documents graph
    # signal, and hard-fail an empty graph when graph aliases are declared.
    assert "/documents" in ep.PROBE_SOURCE
    assert "GRAPH_ALIASES_DECLARED" in ep.PROBE_SOURCE
    assert "processed" in ep.PROBE_SOURCE
    assert "graph EMPTY" in ep.PROBE_SOURCE


def _probe_lightrag(monkeypatch, *, statuses, graph_declared):
    """Exec the in-container PROBE_SOURCE with httpx mocked and return the lightrag
    result. record() isolates each probe, so the other services failing on unset
    env doesn't affect the lightrag verdict — this asserts only the graph gate."""

    class _Resp:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _get(url, *args, **kwargs):
        if url.endswith("/documents"):
            return _Resp({"statuses": statuses})
        return _Resp({})  # /health and any other GET

    monkeypatch.setitem(sys.modules, "httpx", types.SimpleNamespace(get=_get))
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("GRAPH_ALIASES_DECLARED", "1" if graph_declared else "0")
    ns: dict = {}
    exec(compile(ep.PROBE_SOURCE, "<probe>", "exec"), ns)
    return ns["results"]["lightrag"]


def test_probe_lightrag_passes_on_populated_graph(monkeypatch) -> None:
    res = _probe_lightrag(monkeypatch, statuses={"processed": [1, 2, 3]}, graph_declared=True)
    assert res["ok"] is True
    assert "3 processed" in res["detail"]


def test_probe_lightrag_fails_on_empty_graph_when_declared(monkeypatch) -> None:
    res = _probe_lightrag(monkeypatch, statuses={}, graph_declared=True)
    assert res["ok"] is False
    assert "EMPTY" in res["detail"]


def test_probe_lightrag_allows_empty_graph_when_not_declared(monkeypatch) -> None:
    # Vector-only run: no graph aliases declared → an empty graph is expected.
    res = _probe_lightrag(monkeypatch, statuses={}, graph_declared=False)
    assert res["ok"] is True


def test_probe_lightrag_fails_on_failed_docs(monkeypatch) -> None:
    res = _probe_lightrag(
        monkeypatch, statuses={"processed": [1, 2], "failed": [9]}, graph_declared=True
    )
    assert res["ok"] is False
    assert "FAILED" in res["detail"]


def test_ollama_version_skew_detected(monkeypatch) -> None:
    def _run(*args, **kwargs):
        return types.SimpleNamespace(
            stdout="ollama version is 0.32.1\n",
            stderr="Warning: client version is 0.21.0\n",
            returncode=0,
        )

    monkeypatch.setattr(ep.subprocess, "run", _run)
    msg = ep.check_ollama_version_skew()
    assert msg is not None
    assert "0.21.0" in msg and "0.32.1" in msg


def test_ollama_version_skew_none_when_aligned(monkeypatch) -> None:
    def _run(*args, **kwargs):
        return types.SimpleNamespace(stdout="ollama version is 0.32.1\n", stderr="", returncode=0)

    monkeypatch.setattr(ep.subprocess, "run", _run)
    assert ep.check_ollama_version_skew() is None


def test_ollama_version_skew_none_when_cli_absent(monkeypatch) -> None:
    def _run(*args, **kwargs):
        raise FileNotFoundError("ollama")

    monkeypatch.setattr(ep.subprocess, "run", _run)
    assert ep.check_ollama_version_skew() is None


def test_format_report_shows_version_skew_warning() -> None:
    probes = {s: {"ok": True, "detail": "ok"} for s in ep.DECLARED_SERVICES}
    report = ep.format_report({"ok": True, "detail": "passed"}, probes, ["ollama skew: fix it"])
    assert "⚠" in report
    assert "ollama skew: fix it" in report
    # An advisory must not flip the overall result.
    assert "all dependencies ready" in report
