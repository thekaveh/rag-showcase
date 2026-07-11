from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_manifest():
    script = """
import json
import sys
from dataclasses import asdict
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "infra" / "bootstrapper"))
from core.plugin_manifest import load_plugin_manifest

manifest = load_plugin_manifest(root / "backend_plugins" / "rag")
print(json.dumps(asdict(manifest), default=str))
"""
    result = subprocess.run(
        [
            "uv",
            "run",
            "--project",
            str(ROOT / "infra" / "bootstrapper"),
            "python",
            "-c",
            script,
            str(ROOT),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout)


def test_rag_plugin_manifest_declares_shared_route_and_health_contract() -> None:
    manifest = _load_manifest()

    assert manifest["name"] == "rag-showcase"
    assert manifest["route_prefix"] == "/rag"
    assert manifest["health_path"] == "/rag/health"
    assert manifest["docs_url"] == "docs/approaches.md"
    assert manifest["auth"] == "inherit"
    assert set(manifest["depends_on"]) == {
        "litellm",
        "weaviate",
        "tei-reranker",
        "lightrag",
        "n8n",
    }


def test_rag_plugin_manifest_declares_required_files_and_typed_knobs() -> None:
    manifest = _load_manifest()
    env = {entry["name"]: entry for entry in manifest["env"]}

    assert env["RAG_ROLES_FILE"]["required"] is True
    assert env["RAG_FLAVORS_FILE"]["required"] is True
    assert env["LITELLM_API_KEY"]["secret"] is True
    assert env["LIGHTRAG_API_KEY"]["secret"] is True
    assert env["RAG_WEAVIATE_GRPC_PORT"]["type"] == "int"
    assert env["TEI_RERANKER_MAX_BATCH"]["type"] == "int"
    assert env["LIGHTRAG_QUERY_ENABLE_RERANK"]["type"] == "bool"
    for name in (
        "LIGHTRAG_QUERY_TOP_K",
        "LIGHTRAG_QUERY_CHUNK_TOP_K",
        "LIGHTRAG_QUERY_MAX_TOTAL_TOKENS",
        "LIGHTRAG_UPLOAD_RETRIES",
    ):
        assert env[name]["type"] == "int"
    assert env["LIGHTRAG_UPLOAD_RETRY_DELAY"]["type"] == "string"
    assert env["LIGHTRAG_UPLOAD_RETRY_DELAY"]["default"] == "5.0"


def test_manifest_required_files_are_supplied_to_backend_by_consumer_env() -> None:
    env_text = (ROOT / "config" / "atlas.env.user").read_text(encoding="utf-8")
    overlay_text = (ROOT / "compose" / "rag-overlay.yml").read_text(encoding="utf-8")

    assert "RAG_ROLES_FILE=/app/plugins/rag/roles.yaml" in env_text
    assert "RAG_FLAVORS_FILE=/app/plugins/rag/flavors.yaml" in env_text
    assert "RAG_ROLES_FILE: ${RAG_ROLES_FILE:-/app/plugins/rag/roles.yaml}" in overlay_text
    assert "RAG_FLAVORS_FILE: ${RAG_FLAVORS_FILE:-/app/plugins/rag/flavors.yaml}" in overlay_text
