import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _script(name: str) -> str:
    return (ROOT / "scripts" / name).read_text(encoding="utf-8")


def _load_runtime_module():
    path = ROOT / "scripts" / "verify_atlas_runtime.py"
    spec = importlib.util.spec_from_file_location("verify_atlas_runtime", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_start_uses_atlas_consumer_manifest_and_native_headless_preflight() -> None:
    script = _script("start-all.sh")

    assert "ATLAS_CONSUMER_MANIFEST" in script
    assert "atlas.consumer.yml" in script
    assert 'env backfill' in script
    assert 'compose validate' in script
    assert 'doctor --format json' in script
    assert "atlas_preflight.py" not in script
    assert '--consumer "$ATLAS_CONSUMER_MANIFEST"' in script
    assert "--no-tui --detach" in script


def test_start_bridges_litellm_secret_to_cross_provider_lightrag_roles() -> None:
    script = _script("start-all.sh")

    assert (
        "sync_runtime_secret_alias LITELLM_MASTER_KEY "
        "LIGHTRAG_KEYWORD_LLM_BINDING_API_KEY" in script
    )
    assert (
        "sync_runtime_secret_alias LITELLM_MASTER_KEY "
        "LIGHTRAG_QUERY_LLM_BINDING_API_KEY" in script
    )


def test_start_does_not_background_or_kill_atlas() -> None:
    script = _script("start-all.sh")

    assert "ATLAS_START_PID" not in script
    assert "cleanup_atlas_start" not in script
    assert "pkill" not in script
    assert "\ntrap " not in script


def test_stop_is_project_scoped_and_preserves_shared_managed_hosts() -> None:
    script = _script("stop-all.sh")

    assert "docker compose" not in script
    assert 'PROJECT_NAME="${RAG_SHOWCASE_PROJECT_NAME:-rag-showcase}"' in script
    assert 'ATLAS_CONSUMER_MANIFEST=' in script
    assert './stop.sh --project "$PROJECT_NAME"' in script
    assert 'stop_args+=(--cold)' in script
    assert "--stop-managed-hosts" not in script
    assert "Atlas #655" not in script


def test_start_uses_strict_fallback_for_atlas_one_shot_race() -> None:
    script = _script("start-all.sh")

    assert "Waiting for n8n to report healthy" not in script
    assert "Waiting for LightRAG to report healthy" not in script
    assert "Waiting for Weaviate to report ready" not in script
    assert "verify_atlas_runtime.py" in script
    assert "--atlas-log" in script
    assert "Atlas #508" in script
    assert "verify_atlas_runtime.py || true" not in script
    assert script.count("n8n did not recover after workflow activation reload") == 1
    assert "Verifying the Atlas-seeded adaptive-rag production webhook" in script


def test_start_requires_structured_adaptive_rag_webhook_evidence() -> None:
    script = _script("start-all.sh")

    assert "verify_adaptive_webhook.py" in script
    assert script.index("ingest.atlas_job") < script.index("verify_adaptive_webhook.py")
    assert "Deferring adaptive-rag semantic verification until dataset ingestion" in script


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
    config = load_consumer_config(
        ROOT / "infra",
        explicit_paths=[str(manifest)],
    )

    assert config.env_overrides["PROJECT_NAME"] == "rag-showcase"
    assert config.env_overrides["BRAND_TAGLINE"] == (
        "Seven RAG approaches, side by side"
    )
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


def test_start_ready_message_lists_every_base_approach() -> None:
    ready_message = _script("start-all.sh").split("==> Ready.", 1)[1]

    for approach in (
        "vanilla-rag",
        "hybrid-rag",
        "contextual-rag",
        "graph-rag",
        "agentic-rag",
        "n8n-adaptive-rag",
        "lazy-graph-rag",
    ):
        assert approach in ready_message


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

    assert not module.is_exited_zero_race("[ERROR] Configuration validation failed\n")
    assert not module.is_exited_zero_race(
        "container rag-showcase-n8n-init exited (17)\n"
        "[ERROR] Failed to start some services\n"
    )
    assert module.is_exited_zero_race(
        "container rag-showcase-n8n-init exited (0)\n"
        "[ERROR] Failed to start some services\n"
    )


def test_runtime_verifier_accepts_converged_enabled_services() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module)

    pending, failures = module.evaluate(snapshot, "ollama-container-cpu")

    assert pending == []
    assert failures == []
    assert "n8n-seed" in module.ONE_SHOT_SERVICES
    assert "minio" not in module.LONG_LIVED_SERVICES


def test_runtime_verifier_waits_for_starting_services() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module, "ollama-localhost")
    snapshot["backend"] = {
        "Status": "running",
        "Health": {"Status": "starting"},
    }

    pending, failures = module.evaluate(snapshot, "ollama-localhost")

    assert "backend: starting" in pending
    assert failures == []


def test_runtime_verifier_rejects_genuine_failures() -> None:
    module = _load_runtime_module()
    snapshot = _runtime_snapshot(module)
    snapshot["backend"] = {
        "Status": "running",
        "Health": {"Status": "unhealthy"},
    }
    snapshot["n8n-init"] = {"Status": "exited", "ExitCode": 17}

    pending, failures = module.evaluate(snapshot, "ollama-container-cpu")

    assert pending == []
    assert "backend: unhealthy" in failures
    assert "n8n-init: exited 17" in failures
