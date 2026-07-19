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
