from pathlib import Path

import yaml


def test_lightrag_overlay_sets_role_specific_host_ollama_models() -> None:
    overlay = yaml.safe_load(Path("compose/rag-overlay.yml").read_text())

    init_env = overlay["services"]["lightrag-init"]["environment"]
    assert init_env["LIGHTRAG_EMBEDDING_MODEL"] == "${RAG_LIGHTRAG_EMBEDDING_MODEL:-nomic-embed-text}"
    assert init_env["LIGHTRAG_EMBEDDING_DIM"] == "768"

    env = overlay["services"]["lightrag"]["environment"]

    assert env["EMBEDDING_BINDING"] == "ollama"
    assert env["EMBEDDING_BINDING_HOST"] == "http://host.docker.internal:11434"
    assert env["EMBEDDING_BINDING_API_KEY"] == "ollama"
    assert env["EMBEDDING_MODEL"] == "${RAG_LIGHTRAG_EMBEDDING_MODEL:-nomic-embed-text}"
    assert env["EMBEDDING_DIM"] == "768"
    assert env["EMBEDDING_TIMEOUT"] == "${RAG_LIGHTRAG_EMBEDDING_TIMEOUT:-120}"

    assert env["EXTRACT_LLM_BINDING"] == "ollama"
    assert env["EXTRACT_LLM_BINDING_HOST"] == "http://host.docker.internal:11434"
    assert env["EXTRACT_LLM_BINDING_API_KEY"] == "ollama"
    assert env["EXTRACT_LLM_MODEL"] == "${RAG_LIGHTRAG_EXTRACT_MODEL:-mistral-small3.2:24b}"
    assert env["EXTRACT_MAX_ASYNC_LLM"] == "${RAG_LIGHTRAG_EXTRACT_MAX_ASYNC:-1}"
    assert env["EXTRACT_LLM_TIMEOUT"] == "${RAG_LIGHTRAG_EXTRACT_TIMEOUT:-900}"
    assert env["EXTRACT_OLLAMA_LLM_NUM_CTX"] == "${RAG_LIGHTRAG_EXTRACT_NUM_CTX:-8192}"

    assert env["KEYWORD_LLM_BINDING"] == "ollama"
    assert env["KEYWORD_LLM_BINDING_HOST"] == "http://host.docker.internal:11434"
    assert env["KEYWORD_LLM_BINDING_API_KEY"] == "ollama"
    assert env["KEYWORD_LLM_MODEL"] == "${RAG_LIGHTRAG_KEYWORD_MODEL:-mistral-small3.2:24b}"
    assert env["KEYWORD_OLLAMA_LLM_NUM_CTX"] == "${RAG_LIGHTRAG_KEYWORD_NUM_CTX:-8192}"

    assert env["QUERY_LLM_BINDING"] == "ollama"
    assert env["QUERY_LLM_BINDING_HOST"] == "http://host.docker.internal:11434"
    assert env["QUERY_LLM_BINDING_API_KEY"] == "ollama"
    assert env["QUERY_LLM_MODEL"] == "${RAG_LIGHTRAG_QUERY_MODEL:-mistral-small3.2:24b}"
    assert env["QUERY_OLLAMA_LLM_NUM_CTX"] == "${RAG_LIGHTRAG_QUERY_NUM_CTX:-8192}"


def test_backend_overlay_sets_graph_query_safety_defaults() -> None:
    overlay = yaml.safe_load(Path("compose/rag-overlay.yml").read_text())
    env = overlay["services"]["backend"]["environment"]

    assert env["LIGHTRAG_QUERY_ENABLE_RERANK"] == "${LIGHTRAG_QUERY_ENABLE_RERANK:-false}"
    assert env["LIGHTRAG_QUERY_TOP_K"] == "${LIGHTRAG_QUERY_TOP_K:-10}"
    assert env["LIGHTRAG_QUERY_CHUNK_TOP_K"] == "${LIGHTRAG_QUERY_CHUNK_TOP_K:-5}"
    assert env["LIGHTRAG_QUERY_MAX_TOTAL_TOKENS"] == "${LIGHTRAG_QUERY_MAX_TOTAL_TOKENS:-12000}"
