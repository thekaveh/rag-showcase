import importlib.util
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


def test_start_uses_atlas_external_env_and_headless_preflight() -> None:
    script = _script("start-all.sh")

    assert "ATLAS_ENV_USER_FILE" in script
    assert "atlas.env.user" in script
    assert "atlas_preflight.py" in script
    assert "--no-tui --detach" in script


def test_start_does_not_background_or_kill_atlas() -> None:
    script = _script("start-all.sh")

    assert "ATLAS_START_PID" not in script
    assert "cleanup_atlas_start" not in script
    assert "pkill" not in script
    assert "trap" not in script


def test_start_does_not_repeat_atlas_owned_health_gates() -> None:
    script = _script("start-all.sh")

    assert "Waiting for n8n to report healthy" not in script
    assert "Waiting for LightRAG to report healthy" not in script
    assert "Waiting for Weaviate to report ready" not in script
    assert script.count("wait_for_n8n ||") == 1  # only after wrapper-owned restart


def test_start_handles_only_the_atlas_exited_zero_false_negative() -> None:
    script = _script("start-all.sh")

    assert "verify_atlas_runtime.py" in script
    assert "--atlas-log" in script
    assert "Atlas #508" in script
    assert "verify_atlas_runtime.py || true" not in script


def test_setup_overlay_does_not_mutate_atlas_env() -> None:
    script = _script("setup-overlay.sh")

    assert "infra/.env" not in script
    assert "set_env" not in script
    assert "sed -i" not in script


def test_parent_owned_atlas_env_declares_showcase_defaults() -> None:
    env_file = ROOT / "config" / "atlas.env.user"
    values = {}
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key] = value

    assert values["PROJECT_NAME"] == "rag-showcase"
    assert values["BRAND_NAME"] == "RAG-SHOWCASE"
    assert values["BRAND_LOGO_FILE"] == "../../brand/rag-showcase.logo"
    assert values["LIGHTRAG_EMBEDDING_MODEL"] == "nomic-embed-text"
    assert values["LIGHTRAG_EXTRACT_LLM_MODEL"] == "mistral-small3.2:24b"
    assert values["LIGHTRAG_KEYWORD_LLM_MODEL"] == "mistral-small3.2:24b"
    assert values["LIGHTRAG_QUERY_LLM_MODEL"] == "mistral-small3.2:24b"
    assert "mistral-small3.2:24b" in values["OLLAMA_CUSTOM_MODELS"].split(",")


def test_preflight_parser_matches_atlas_env_overlay_semantics(tmp_path) -> None:
    module = _load_preflight_module()
    env_file = tmp_path / "atlas.env.user"
    env_file.write_text(
        "PLAIN=value\n"
        "SPACED=hello world # comment\n"
        "QUOTED=\"hello # world\" # comment\n"
        "EQUALS=a=b=c\n",
        encoding="utf-8",
    )

    assert module.parse_env_overlay(env_file) == {
        "PLAIN": "value",
        "SPACED": "hello world",
        "QUOTED": "hello # world",
        "EQUALS": "a=b=c",
    }


def test_preflight_invokes_supported_atlas_commands() -> None:
    script = _script("atlas_preflight.py")

    assert '("./start.sh", "env", "backfill")' in script
    assert '("./start.sh", "compose", "validate")' in script


def test_preflight_uses_temporary_env_without_exporting_overlay_keys(
    tmp_path, monkeypatch
) -> None:
    module = _load_preflight_module()
    infra = tmp_path / "infra"
    infra.mkdir()
    (infra / ".env").write_text("BASE=original\nPATH=/safe\n", encoding="utf-8")
    overlay = tmp_path / "atlas.env.user"
    overlay.write_text(
        "PROJECT_NAME=test-project\n"
        "BASE=override\n"
        "PATH=/untrusted\n"
        'QUOTED="hello # world" # comment\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(module, "ROOT", tmp_path)
    monkeypatch.setenv("PATH", "/host/path")

    calls = []

    def fake_run(command, *, cwd, env, check):
        calls.append(
            {
                "command": command,
                "cwd": cwd,
                "path": env["PATH"],
                "env_file": Path(env["ATLAS_ENV_FILE"]).read_text(encoding="utf-8"),
                "check": check,
            }
        )

    monkeypatch.setattr(module.subprocess, "run", fake_run)
    module.run_preflight(overlay)

    assert [call["command"] for call in calls] == [
        ("./start.sh", "env", "backfill"),
        ("./start.sh", "compose", "validate"),
    ]
    assert all(call["cwd"] == infra for call in calls)
    assert all(call["path"] == "/host/path" for call in calls)
    assert all("BASE=original" not in call["env_file"] for call in calls)
    assert all("BASE=override" in call["env_file"] for call in calls)
    assert all("PATH=/safe" not in call["env_file"] for call in calls)
    assert all("PATH=/untrusted" in call["env_file"] for call in calls)
    assert all("QUOTED=hello # world" in call["env_file"] for call in calls)
    assert all('QUOTED="hello # world"' not in call["env_file"] for call in calls)


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
