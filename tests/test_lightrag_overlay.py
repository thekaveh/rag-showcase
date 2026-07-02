from pathlib import Path

import yaml


def test_lightrag_overlay_delegates_lightrag_service_config_to_atlas() -> None:
    overlay = yaml.safe_load(Path("compose/rag-overlay.yml").read_text())

    assert "lightrag" not in overlay["services"]
    assert "lightrag-init" not in overlay["services"]


def test_setup_overlay_sets_atlas_lightrag_inputs_not_native_runtime_envs() -> None:
    script = Path("scripts/setup-overlay.sh").read_text()

    assert "set_env_default LIGHTRAG_EXTRACT_LLM_MODEL" in script
    assert "set_env_default LIGHTRAG_KEYWORD_LLM_MODEL" in script
    assert "set_env_default LIGHTRAG_QUERY_LLM_MODEL" in script
    assert "append_csv_env OLLAMA_CUSTOM_MODELS" in script

    assert "set_env_default EXTRACT_LLM_MODEL" not in script
    assert "set_env_default KEYWORD_LLM_MODEL" not in script
    assert "set_env_default QUERY_LLM_MODEL" not in script
    assert "host.docker.internal:11434" not in script


def test_backend_overlay_sets_graph_query_safety_defaults() -> None:
    overlay = yaml.safe_load(Path("compose/rag-overlay.yml").read_text())
    env = overlay["services"]["backend"]["environment"]

    assert env["LIGHTRAG_QUERY_ENABLE_RERANK"] == "${LIGHTRAG_QUERY_ENABLE_RERANK:-false}"
    assert env["LIGHTRAG_QUERY_TOP_K"] == "${LIGHTRAG_QUERY_TOP_K:-10}"
    assert env["LIGHTRAG_QUERY_CHUNK_TOP_K"] == "${LIGHTRAG_QUERY_CHUNK_TOP_K:-5}"
    assert env["LIGHTRAG_QUERY_MAX_TOTAL_TOKENS"] == "${LIGHTRAG_QUERY_MAX_TOTAL_TOKENS:-12000}"
