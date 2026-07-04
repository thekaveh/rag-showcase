from pathlib import Path

import yaml

# Anchor to the repo root so the suite passes from any CWD (siblings do the same).
ROOT = Path(__file__).resolve().parents[1]


def test_lightrag_overlay_only_adds_optional_lightrag_ollama_context_caps() -> None:
    overlay = yaml.safe_load((ROOT / "compose/rag-overlay.yml").read_text(encoding="utf-8"))
    env = overlay["services"]["lightrag"]["environment"]

    assert "lightrag-init" not in overlay["services"]
    assert env == {
        "OLLAMA_LLM_NUM_CTX": "${LIGHTRAG_OLLAMA_LLM_NUM_CTX:-8192}",
        "EXTRACT_OLLAMA_LLM_NUM_CTX": "${LIGHTRAG_EXTRACT_OLLAMA_LLM_NUM_CTX:-8192}",
        "KEYWORD_OLLAMA_LLM_NUM_CTX": "${LIGHTRAG_KEYWORD_OLLAMA_LLM_NUM_CTX:-8192}",
        "QUERY_OLLAMA_LLM_NUM_CTX": "${LIGHTRAG_QUERY_OLLAMA_LLM_NUM_CTX:-8192}",
    }


def test_setup_overlay_sets_atlas_lightrag_inputs_not_native_runtime_envs() -> None:
    script = (ROOT / "scripts/setup-overlay.sh").read_text(encoding="utf-8")

    assert "set_env_default LIGHTRAG_EXTRACT_LLM_MODEL" in script
    assert "set_env_default LIGHTRAG_KEYWORD_LLM_MODEL" in script
    assert "set_env_default LIGHTRAG_QUERY_LLM_MODEL" in script
    assert "append_csv_env OLLAMA_CUSTOM_MODELS" in script

    assert "set_env_default EXTRACT_LLM_MODEL" not in script
    assert "set_env_default KEYWORD_LLM_MODEL" not in script
    assert "set_env_default QUERY_LLM_MODEL" not in script
    assert "host.docker.internal:11434" not in script


def test_backend_overlay_sets_graph_query_safety_defaults() -> None:
    overlay = yaml.safe_load((ROOT / "compose/rag-overlay.yml").read_text(encoding="utf-8"))
    env = overlay["services"]["backend"]["environment"]

    assert env["LIGHTRAG_QUERY_ENABLE_RERANK"] == "${LIGHTRAG_QUERY_ENABLE_RERANK:-false}"
    assert env["LIGHTRAG_QUERY_TOP_K"] == "${LIGHTRAG_QUERY_TOP_K:-10}"
    assert env["LIGHTRAG_QUERY_CHUNK_TOP_K"] == "${LIGHTRAG_QUERY_CHUNK_TOP_K:-5}"
    assert env["LIGHTRAG_QUERY_MAX_TOTAL_TOKENS"] == "${LIGHTRAG_QUERY_MAX_TOTAL_TOKENS:-12000}"
