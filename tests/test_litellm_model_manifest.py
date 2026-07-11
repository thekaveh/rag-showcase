from __future__ import annotations

import json
import subprocess
from pathlib import Path

import yaml

from compare import flavors


ROOT = Path(__file__).resolve().parents[1]


def _load_consumer_models() -> list[dict]:
    script = """
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root / "infra" / "bootstrapper"))
from core.consumer_manifest import load_consumer_config

config = load_consumer_config(
    root / "infra", explicit_paths=[str(root / "atlas.consumer.yml")]
)
print(json.dumps([model.to_row() for model in config.litellm_models]))
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


def _expected_aliases() -> dict[str, str]:
    aliases = {name: name for name in flavors.BASE_APPROACHES}
    manifest = yaml.safe_load(
        (ROOT / "backend_plugins" / "rag" / "flavors.yaml").read_text(encoding="utf-8")
    )
    aliases.update({row["alias"]: row["base"] for row in manifest["flavors"]})
    return aliases


def test_consumer_manifest_declares_every_base_and_flavor_alias() -> None:
    rows = _load_consumer_models()
    expected = _expected_aliases()

    assert {row["model_name"] for row in rows} == set(expected)
    assert len(rows) == 14

    for row in rows:
        alias = row["model_name"]
        params = row["litellm_params"]
        info = row["model_info"]
        assert params["model"] == f"openai/{alias}"
        assert params["api_base"] == f"http://backend:8000/rag/{expected[alias]}/v1"
        assert params["api_key"] == "os.environ/LITELLM_MASTER_KEY"
        assert info["atlas_owner"] == "rag-showcase"
        assert info["atlas_managed"] is True
        assert info["base_approach"] == expected[alias]
        assert info["flavor"] is (alias != expected[alias])


def test_aliases_are_declarative_and_startup_only_waits_for_them() -> None:
    script = (ROOT / "scripts" / "start-all.sh").read_text(encoding="utf-8")
    overlay = (ROOT / "compose" / "rag-overlay.yml").read_text(encoding="utf-8")

    assert "register_models.py" not in script
    assert "/model/new" not in script
    assert "../register:/app/register" not in overlay
    assert "reconcile_litellm_aliases.py" in script
    assert "infra/volumes/litellm/consumer-models.yaml" in script
    assert '--changed-file "$ALIAS_CHANGE_FILE"' in script
    assert 'docker restart "${PROJECT_NAME}-litellm"' in script
    assert "required = {" not in script
    assert ".rag-showcase-alias-migration" not in script
    for alias, base in _expected_aliases().items():
        if alias != base:
            assert alias not in script
