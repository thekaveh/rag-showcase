#!/usr/bin/env python3
"""Run Atlas headless checks under the selected parent-owned env overlay."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def parse_env_overlay(path: Path) -> dict[str, str]:
    """Parse the dotenv subset supported by Atlas external env overlays."""
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        value = value.strip()
        if value[:1] in ('"', "'"):
            quote = value[0]
            end = value.find(quote, 1)
            value = value[1:end] if end != -1 else value.strip('"\'')
        else:
            for index, char in enumerate(value):
                if char == "#" and (index == 0 or value[index - 1] in " \t"):
                    value = value[:index]
                    break
            value = value.strip()
        values[key.strip()] = value
    return values


def merge_env_overrides(content: str, overrides: dict[str, str]) -> str:
    """Apply parsed overlay values using Atlas's replace-or-append semantics."""
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


def run_preflight(overlay: Path) -> None:
    """Validate a temporary active env containing the consumer overlay."""
    if not overlay.is_file():
        raise SystemExit(f"Atlas env overlay is missing or unreadable: {overlay}")
    overrides = parse_env_overlay(overlay)
    if "PROJECT_NAME" not in overrides:
        raise SystemExit(f"Atlas env overlay must declare PROJECT_NAME: {overlay}")

    infra = ROOT / "infra"
    active_env = infra / ".env"
    baseline = active_env if active_env.is_file() else infra / ".env.example"
    if not baseline.is_file():
        raise SystemExit(f"Atlas env baseline is missing: {baseline}")

    merged = merge_env_overrides(baseline.read_text(encoding="utf-8"), overrides)
    command_env = os.environ.copy()
    command_env["ATLAS_ENV_USER_FILE"] = str(overlay)

    with tempfile.TemporaryDirectory(prefix="rag-showcase-atlas-") as temp_dir:
        env_file = Path(temp_dir) / ".env"
        env_file.write_text(merged, encoding="utf-8")
        command_env["ATLAS_ENV_FILE"] = str(env_file)
        for command in (
            ("./start.sh", "env", "backfill"),
            ("./start.sh", "compose", "validate"),
        ):
            subprocess.run(command, cwd=infra, env=command_env, check=True)


def main() -> None:
    overlay = Path(os.environ["ATLAS_ENV_USER_FILE"]).expanduser().resolve()
    run_preflight(overlay)


if __name__ == "__main__":
    main()
