import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script(name: str) -> str:
    return (ROOT / "scripts" / name).read_text(encoding="utf-8")


def _load_preflight_module():
    path = ROOT / "scripts" / "atlas_preflight.py"
    spec = importlib.util.spec_from_file_location("atlas_preflight", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_runtime_module():
    path = ROOT / "scripts" / "verify_atlas_runtime.py"
    spec = importlib.util.spec_from_file_location("verify_atlas_runtime", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_start_uses_atlas_consumer_manifest_and_headless_preflight() -> None:
    script = _script("start-all.sh")

    assert "ATLAS_CONSUMER_MANIFEST" in script
    assert "atlas.consumer.yml" in script
    assert (
        'uv run --project "$ROOT/infra/bootstrapper" '
        "python scripts/atlas_preflight.py" in script
    )
    assert "\npython3 scripts/atlas_preflight.py" not in script
    assert '--consumer "$ATLAS_CONSUMER_MANIFEST"' in script
    assert "--no-tui --detach" in script


def test_start_does_not_background_or_kill_atlas() -> None:
    script = _script("start-all.sh")

    assert "ATLAS_START_PID" not in script
    assert "cleanup_atlas_start" not in script
    assert "pkill" not in script
    assert "\ntrap " not in script


def test_start_does_not_repeat_atlas_owned_health_gates() -> None:
    script = _script("start-all.sh")

    assert "Waiting for n8n to report healthy" not in script
    assert "Waiting for LightRAG to report healthy" not in script
    assert "Waiting for Weaviate to report ready" not in script
    assert script.count("n8n did not recover after workflow activation reload") == 1
    assert "Verifying the Atlas-seeded adaptive-rag production webhook" in script


def test_start_handles_only_the_atlas_exited_zero_false_negative() -> None:
    script = _script("start-all.sh")

    assert "verify_atlas_runtime.py" in script
    assert "--atlas-log" in script
    assert "Atlas #508" in script
    assert "verify_atlas_runtime.py || true" not in script


def test_start_does_not_create_a_user_overlay_symlink() -> None:
    script = _script("start-all.sh")

    assert "setup-overlay.sh" not in script
    assert "ln -s" not in script
    assert "LEGACY_OVERLAY" in script
    assert not (ROOT / "scripts" / "setup-overlay.sh").exists()


def test_consumer_manifest_declares_the_atlas_integration() -> None:
    bootstrapper = str(ROOT / "infra" / "bootstrapper")
    if bootstrapper not in sys.path:
        sys.path.insert(0, bootstrapper)
    from core.consumer_manifest import load_consumer_config

    manifest = ROOT / "atlas.consumer.yml"
    config = load_consumer_config(ROOT / "infra", explicit_paths=[str(manifest)])

    assert config.env_overrides["PROJECT_NAME"] == "rag-showcase"
    assert config.env_overrides["BRAND_NAME"] == "RAG-SHOWCASE"
    assert config.env_overrides["BRAND_LOGO_FILE"] == str(
        (ROOT / "brand" / "rag-showcase.logo").resolve()
    )
    assert config.env_overrides["LIGHTRAG_EMBEDDING_MODEL"] == "nomic-embed-text"
    assert config.env_overrides["LIGHTRAG_EXTRACT_LLM_MODEL"] == "mistral-small3.2:24b"
    assert config.env_overrides["LIGHTRAG_KEYWORD_LLM_MODEL"] == "qwen3.6:latest"
    assert config.env_overrides["LIGHTRAG_QUERY_LLM_MODEL"] == "qwen3.6:latest"
    assert config.env_overrides["OLLAMA_CUSTOM_MODELS"] == "mistral-small3.2:24b"
    assert config.compose_overlays == [ROOT / "compose" / "rag-overlay.yml"]
    assert list(config.consumers[0].backend_plugins) == [ROOT / "backend_plugins"]


def test_preflight_invokes_supported_atlas_commands() -> None:
    script = _script("atlas_preflight.py")

    assert '"env", "backfill"' in script
    assert '"compose", "validate"' in script
    assert '"doctor", "--format", "json"' in script
    assert '"--consumer"' in script


def test_preflight_validates_manifest_assembled_environment(monkeypatch) -> None:
    module = _load_preflight_module()
    infra = ROOT / "infra"
    manifest = ROOT / "atlas.consumer.yml"
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    monkeypatch.delenv("BACKEND_PLUGINS_DIR", raising=False)

    calls = []

    def fake_run(command, *, cwd, env, check):
        active_env = Path(env["ATLAS_ENV_FILE"])
        calls.append((command, cwd, env.copy(), check, active_env.read_text()))

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.run_preflight(manifest)

    expected_prefix = ("./start.sh", "--consumer", str(manifest.resolve()))
    assert [call[0] for call in calls] == [
        (*expected_prefix, "env", "backfill"),
        (*expected_prefix, "compose", "validate"),
        (*expected_prefix, "doctor", "--format", "json"),
    ]
    assert all(call[1] == infra for call in calls)
    assert all(call[2]["ATLAS_CONSUMER_MANIFEST"] == str(manifest.resolve()) for call in calls)
    assert all(call[3] is True for call in calls)
    assert all("PROJECT_NAME=rag-showcase" in call[4] for call in calls)
    assert all(f"BACKEND_PLUGINS_DIR={ROOT / 'backend_plugins'}" in call[4] for call in calls)
    assert all("OLLAMA_CUSTOM_MODELS=mistral-small3.2:24b" in call[4] for call in calls)
    assert all("LIGHTRAG_EXTRACT_LLM_MODEL=mistral-small3.2:24b" in call[4] for call in calls)
    assert all(call[2]["PATH"] == module.os.environ["PATH"] for call in calls)
    assert all("PROJECT_NAME" not in call[2] for call in calls)
    assert all("BACKEND_PLUGINS_DIR" not in call[2] for call in calls)


def _runtime_snapshot(module, llm_source="ollama-container-cpu"):
    long_lived, one_shots = module.required_services(llm_source)
    snapshot = {
        service: {"Status": "running", "Health": {"Status": "healthy"}}
        for service in long_lived
    }
    snapshot.update(
        {
            service: {"Status": "exited", "ExitCode": 0}
            for service in one_shots
        }
    )
    return snapshot


def test_runtime_verifier_requires_exact_atlas_exited_zero_signature() -> None:
    module = _load_runtime_module()
    assert not module.is_exited_zero_race(
        "[ERROR] Configuration validation failed\n"
    )
    assert not module.is_exited_zero_race(
        "container rag-showcase-n8n-init exited (17)\n"
        "[ERROR] Failed to start some services\n"
    )
    assert module.is_exited_zero_race(
        "container rag-showcase-n8n-init exited (0)\n"
        "[ERROR] Failed to start some services\n"
    )


def test_runtime_verifier_accepts_healthy_services_and_zero_exit_inits() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module)

    pending, failures = module.evaluate(snapshot, "ollama-container-cpu")
    assert pending == []
    assert failures == []


def test_runtime_verifier_requires_container_ollama_and_pull_job() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module)
    snapshot.pop("ollama")
    snapshot["ollama-pull"] = {"Status": "exited", "ExitCode": 9}

    pending, failures = module.evaluate(snapshot, "ollama-container-cpu")

    assert "ollama: missing" in pending
    assert "ollama-pull: exited 9" in failures


def test_runtime_verifier_does_not_require_ollama_for_host_source() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module, "ollama-localhost")

    pending, failures = module.evaluate(snapshot, "ollama-localhost")

    assert pending == []
    assert failures == []


def test_runtime_verifier_rejects_real_failures() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module)
    snapshot["backend"] = {"Status": "running", "Health": {"Status": "unhealthy"}}
    snapshot["n8n-init"] = {"Status": "exited", "ExitCode": 17}

    pending, failures = module.evaluate(snapshot, "ollama-container-cpu")
    assert pending == []
    assert "backend: unhealthy" in failures
    assert "n8n-init: exited 17" in failures


def test_runtime_verifier_keeps_starting_and_missing_services_pending() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module)
    snapshot["backend"] = {"Status": "running", "Health": {"Status": "starting"}}
    snapshot.pop("lightrag-init")

    pending, failures = module.evaluate(snapshot, "ollama-container-cpu")
    assert "backend: starting" in pending
    assert any(item.startswith("lightrag-init: missing") for item in pending)
    assert failures == []
