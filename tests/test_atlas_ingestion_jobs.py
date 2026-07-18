from __future__ import annotations

import json
import subprocess
from pathlib import Path

import httpx
import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


def _load_profile_contract() -> dict:
    script = """
import json
import sys
from dataclasses import asdict
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "infra" / "bootstrapper"))
from core.consumer_manifest import (
    compile_rag_ingestion_profiles_file,
    load_consumer_config,
)

config = load_consumer_config(
    root / "infra",
    explicit_paths=[str(root / "atlas.consumer.yml")],
)
profiles = list(config.rag_ingestion_profiles)
print(json.dumps({
    "profiles": [asdict(profile) | {"revision": profile.revision} for profile in profiles],
    "compiled": json.loads(compile_rag_ingestion_profiles_file(profiles)),
    "overlay": config.rag_ingestion_overlay.content if config.rag_ingestion_overlay else None,
}, default=str))
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


def test_every_dataset_declares_an_atlas_ingestion_profile() -> None:
    datasets = yaml.safe_load(
        (ROOT / "compare" / "datasets.yaml").read_text(encoding="utf-8")
    )["datasets"]
    contract = _load_profile_contract()
    profiles = {profile["name"]: profile for profile in contract["profiles"]}

    assert "showcase_default" in profiles
    for dataset in datasets:
        profile_name = dataset["ingestion_profile"]
        profile = profiles[profile_name]
        assert profile_name == dataset["id"]
        assert profile["consumer"] == "rag-showcase"
        assert profile["corpus"] == {
            "source": "mount",
            "path": dataset["corpus_path"].removeprefix("corpus/"),
            "bucket": None,
            "prefix": None,
            "access_key_var": None,
            "secret_key_var": None,
        }
        assert profile["parser_order"][-1] == "plain_text"
        assert profile["chunker"] == {
            "strategy": "recursive",
            "chunk_size": 800,
            "overlap": 100,
        }
        assert profile["vector_targets"] == [
            {
                "backend": "weaviate",
                "collection_prefix": "RagBase",
                "on_unavailable": "fail",
            }
        ]
        assert profile["graph_targets"] == [
            {
                "backend": "lightrag",
                "mode": "upload_documents",
                "wait_for_extraction": True,
                "timeout_seconds": 3600,
                "on_unavailable": "fail",
            }
        ]

    compiled_names = {profile["name"] for profile in contract["compiled"]["profiles"]}
    assert compiled_names == set(profiles)
    assert "RAG_INGESTION_PROFILES_FILE" in contract["overlay"]


def test_headless_job_client_waits_for_phase_complete_record() -> None:
    from ingest.atlas_job import run_ingestion

    calls = {"get": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-internal-token"
        if request.method == "POST":
            assert request.url.path == "/api/rag/ingestions"
            assert request.extensions["timeout"]["read"] == 70
            assert json.loads(request.content) == {
                "profile": "baseline_curated",
                "corpus_path": None,
            }
            return httpx.Response(
                202,
                json={
                    "ingestion_id": "job-1",
                    "job_id": "celery-1",
                    "status": "pending",
                    "message": "queued",
                    "task": "rag_ingestion",
                },
            )
        calls["get"] += 1
        status = "running" if calls["get"] == 1 else "completed"
        return httpx.Response(
            200,
            json={
                "id": "job-1",
                "consumer": "rag-showcase",
                "profile": "baseline_curated",
                "revision": "rev-1",
                "idempotency_key": "key-1",
                "status": status,
                "phases": [
                    {"name": "discover", "status": "completed", "counts": {"files": 11}},
                    {"name": "finalize", "status": status},
                ],
                "counts": {"files_discovered": 11, "vectors_written": 22},
                "errors": [],
                "content_digest": "digest-1",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        record = run_ingestion(
            "baseline_curated",
            base_url="http://atlas.test",
            api_token="test-internal-token",
            timeout_seconds=10,
            poll_seconds=0,
            client=client,
        )

    assert record["status"] == "completed"
    assert record["revision"] == "rev-1"
    assert record["content_digest"] == "digest-1"
    assert calls["get"] == 2


def test_headless_job_client_surfaces_phase_failures() -> None:
    from ingest.atlas_job import run_ingestion

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-internal-token"
        if request.method == "POST":
            return httpx.Response(
                202,
                json={
                    "ingestion_id": "job-bad",
                    "status": "pending",
                    "message": "queued",
                    "task": "rag_ingestion",
                },
            )
        return httpx.Response(
            200,
            json={
                "id": "job-bad",
                "consumer": "rag-showcase",
                "profile": "graph_native",
                "revision": "rev-bad",
                "idempotency_key": "key-bad",
                "status": "failed",
                "phases": [{"name": "lightrag_upload", "status": "failed"}],
                "counts": {},
                "errors": [
                    {
                        "phase": "lightrag_upload",
                        "service": "lightrag",
                        "message": "HTTP 422",
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(
            RuntimeError, match="lightrag_upload.*lightrag.*HTTP 422"
        ):
            run_ingestion(
                "graph_native",
                base_url="http://atlas.test",
                api_token="test-internal-token",
                timeout_seconds=10,
                poll_seconds=0,
                client=client,
            )
