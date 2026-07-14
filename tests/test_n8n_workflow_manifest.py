from __future__ import annotations

import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _load_workflow_contract() -> dict:
    script = """
import json
import sys
from dataclasses import asdict
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "infra" / "bootstrapper"))
from core.consumer_manifest import (
    compile_n8n_normalized_workflow,
    compile_n8n_plan,
    load_consumer_config,
)

config = load_consumer_config(
    root / "infra", explicit_paths=[str(root / "atlas.consumer.yml")]
)
workflows = list(config.n8n_workflows)
print(json.dumps({
    "workflows": [asdict(workflow) for workflow in workflows],
    "normalized": [json.loads(compile_n8n_normalized_workflow(workflow)) for workflow in workflows],
    "plan": json.loads(compile_n8n_plan(workflows)),
    "overlay": config.n8n_overlay.content if config.n8n_overlay else None,
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


def test_consumer_manifest_declares_owned_active_adaptive_workflow() -> None:
    contract = _load_workflow_contract()

    assert len(contract["workflows"]) == 1
    workflow = contract["workflows"][0]
    assert workflow["consumer"] == "rag-showcase"
    assert workflow["id"] == "adaptive-rag"
    assert workflow["active"] == "fromJson"
    assert workflow["source_path"] == str(ROOT / "n8n" / "adaptive-rag.workflow.json")
    assert workflow["webhooks"] == [
        {
            "path": "/webhook/adaptive-rag",
            "method": "POST",
            "expect_status": 200,
            "probe": True,
        }
    ]

    normalized = contract["normalized"][0]
    assert normalized["id"] == "atlas-consumer-adaptive-rag"
    assert normalized["active"] is True
    assert contract["plan"]["workflows"][0]["seed_id"] == "atlas-consumer-adaptive-rag"
    assert "n8n-seed:" in contract["overlay"]


def test_workflow_seeding_has_no_showcase_mount_or_manual_import() -> None:
    overlay = (ROOT / "compose" / "rag-overlay.yml").read_text(encoding="utf-8")
    start = (ROOT / "scripts" / "start-all.sh").read_text(encoding="utf-8")
    migration = (ROOT / "scripts" / "remove_legacy_n8n_workflow.js").read_text(
        encoding="utf-8"
    )

    assert "../n8n:/showcase-n8n" not in overlay
    assert "n8n import:workflow" not in start
    assert "--activeState=fromJson" not in start
    assert "/showcase-n8n" not in start
    assert 'if [ -z "$(envval N8N_API_KEY)" ]' in start
    assert "publish:workflow --id=atlas-consumer-adaptive-rag" in start
    assert 'docker restart "${PROJECT_NAME}-n8n"' in start
    assert "remove_legacy_n8n_workflow.js" in start
    assert "unpublish:workflow --id=adaptiverag00001" not in start
    assert "N8N_ADAPTIVE_WEBHOOK_URL" in start
    assert 'response.json().get("answer")' in start

    assert "adaptiverag00001" in migration
    assert "workflow_entity" in migration
    assert "WHERE id = $1" in migration
    assert "DELETE FROM" in migration
