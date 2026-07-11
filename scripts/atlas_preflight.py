#!/usr/bin/env python3
"""Run Atlas headless checks for the selected consumer manifest."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def merge_env_overrides(content: str, overrides: dict[str, str]) -> str:
    """Apply Atlas consumer values using Atlas's replace-or-append semantics."""
    merged = content
    for key, value in overrides.items():
        pattern = rf"^{re.escape(key)}=.*$"
        assignment = f"{key}={value}"
        if re.search(pattern, merged, flags=re.MULTILINE):
            merged = re.sub(
                pattern,
                lambda _match, assignment=assignment: assignment,
                merged,
                flags=re.MULTILINE,
            )
        else:
            if merged and not merged.endswith("\n"):
                merged += "\n"
            merged += assignment + "\n"
    return merged


def load_manifest_overrides(infra: Path, manifest: Path) -> dict[str, str]:
    """Resolve consumer env through the pinned Atlas manifest implementation."""
    bootstrapper = str(infra / "bootstrapper")
    if bootstrapper not in sys.path:
        sys.path.insert(0, bootstrapper)
    from core.consumer_manifest import load_consumer_config

    config = load_consumer_config(infra, explicit_paths=[str(manifest)])
    return config.env_overrides


def run_preflight(manifest: Path) -> None:
    """Validate a temporary active env assembled from the consumer manifest."""
    manifest = manifest.expanduser().resolve()
    if not manifest.is_file():
        raise SystemExit(f"Atlas consumer manifest is missing: {manifest}")
    infra = ROOT / "infra"
    active_env = infra / ".env"
    baseline = active_env if active_env.is_file() else infra / ".env.example"
    if not baseline.is_file():
        raise SystemExit(f"Atlas env baseline is missing: {baseline}")

    overrides = load_manifest_overrides(infra, manifest)
    merged = merge_env_overrides(baseline.read_text(encoding="utf-8"), overrides)
    command_env = os.environ.copy()
    command_env["ATLAS_CONSUMER_MANIFEST"] = str(manifest)
    prefix = ("./start.sh", "--consumer", str(manifest))
    with tempfile.TemporaryDirectory(prefix="rag-showcase-atlas-") as temp_dir:
        env_file = Path(temp_dir) / ".env"
        env_file.write_text(merged, encoding="utf-8")
        command_env["ATLAS_ENV_FILE"] = str(env_file)
        for suffix in (
            ("env", "backfill"),
            ("compose", "validate"),
            ("doctor", "--format", "json"),
        ):
            subprocess.run((*prefix, *suffix), cwd=infra, env=command_env, check=True)


def main() -> None:
    run_preflight(Path(os.environ["ATLAS_CONSUMER_MANIFEST"]))


if __name__ == "__main__":
    main()
