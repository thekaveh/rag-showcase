#!/usr/bin/env python3
"""Wait for Atlas after Compose's successful one-shot wait race."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

LONG_LIVED_SERVICES = {
    "backend",
    "kong-api-gateway",
    "lightrag",
    "litellm",
    "local-deep-researcher",
    "n8n",
    "n8n-worker",
    "neo4j-graph-db",
    "open-web-ui",
    "redis",
    "searxng",
    "supabase-api",
    "supabase-auth",
    "supabase-db",
    "supabase-meta",
    "supabase-realtime",
    "supabase-storage",
    "supabase-studio",
    "tei-reranker",
    "weaviate",
}

ONE_SHOT_SERVICES = {
    "lightrag-init",
    "litellm-init",
    "n8n-init",
    "n8n-seed",
    "open-webui-init",
    "supabase-db-init",
    "weaviate-init",
}

EXITED_ZERO_LINE = re.compile(r"\bcontainer\s+\S+\s+exited\s+\(0\)", re.IGNORECASE)
FAILED_START_SUMMARY = "[ERROR] Failed to start some services"


def env_value(name: str) -> str:
    value = ""
    env_file = ROOT / "infra" / ".env"
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        if raw_line.startswith(f"{name}="):
            value = raw_line.split("=", 1)[1].strip()
    return value


def is_exited_zero_race(output: str) -> bool:
    """Recognize only the Atlas/Compose exited-zero false failure."""
    return bool(EXITED_ZERO_LINE.search(output)) and FAILED_START_SUMMARY in output


def required_services(llm_source: str) -> tuple[set[str], set[str]]:
    long_lived = set(LONG_LIVED_SERVICES)
    one_shots = set(ONE_SHOT_SERVICES)
    if llm_source.startswith("ollama-container-"):
        long_lived.add("ollama")
        one_shots.add("ollama-pull")
    return long_lived, one_shots


def docker_snapshot(project: str) -> dict[str, dict[str, Any]]:
    ids = subprocess.run(
        [
            "docker",
            "ps",
            "-aq",
            "--filter",
            f"label=com.docker.compose.project={project}",
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split()
    if not ids:
        return {}

    inspected = subprocess.run(
        ["docker", "inspect", *ids],
        check=True,
        capture_output=True,
        text=True,
    )
    snapshot: dict[str, dict[str, Any]] = {}
    for item in json.loads(inspected.stdout):
        labels = item.get("Config", {}).get("Labels", {}) or {}
        service = labels.get("com.docker.compose.service")
        if service:
            snapshot[str(service)] = item.get("State", {}) or {}
    return snapshot


def evaluate(
    snapshot: dict[str, dict[str, Any]], llm_source: str
) -> tuple[list[str], list[str]]:
    pending: list[str] = []
    failures: list[str] = []
    long_lived, one_shots = required_services(llm_source)

    for service in sorted(long_lived):
        state = snapshot.get(service)
        if state is None:
            pending.append(f"{service}: missing")
            continue
        status = str(state.get("Status", "unknown")).lower()
        health = str((state.get("Health") or {}).get("Status", "")).lower()
        if status == "running" and health in {"", "healthy"}:
            continue
        if status == "running" and health == "starting":
            pending.append(f"{service}: starting")
        elif status in {"created", "restarting"}:
            pending.append(f"{service}: {status}")
        elif health == "unhealthy":
            failures.append(f"{service}: unhealthy")
        else:
            failures.append(f"{service}: {status}")

    for service in sorted(one_shots):
        state = snapshot.get(service)
        if state is None:
            pending.append(f"{service}: missing")
            continue
        status = str(state.get("Status", "unknown")).lower()
        exit_code = state.get("ExitCode")
        if status == "exited" and exit_code == 0:
            continue
        if status == "exited":
            failures.append(f"{service}: exited {exit_code}")
        elif status in {"created", "running", "restarting"}:
            pending.append(f"{service}: {status}")
        else:
            failures.append(f"{service}: {status}")

    return pending, failures


def wait_for_runtime(project: str, llm_source: str, timeout: float = 300.0) -> bool:
    deadline = time.monotonic() + timeout
    last_pending: list[str] = []
    while time.monotonic() < deadline:
        pending, failures = evaluate(docker_snapshot(project), llm_source)
        if failures:
            print("Atlas runtime contains genuine failures:")
            for failure in failures:
                print(f"  - {failure}")
            return False
        if not pending:
            return True
        last_pending = pending
        time.sleep(2)

    print("Atlas runtime did not converge after detached startup:")
    for item in last_pending:
        print(f"  - {item}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=env_value("PROJECT_NAME"))
    parser.add_argument("--llm-source", default=env_value("LLM_PROVIDER_SOURCE"))
    parser.add_argument("--atlas-log", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=300.0)
    args = parser.parse_args()
    output = args.atlas_log.read_text(encoding="utf-8", errors="replace")
    if not is_exited_zero_race(output):
        raise SystemExit(
            "Atlas failed without the exited-zero signature; refusing fallback."
        )
    if not args.project or not args.llm_source:
        raise SystemExit("PROJECT_NAME or LLM_PROVIDER_SOURCE is missing from infra/.env")
    if not wait_for_runtime(args.project, args.llm_source, args.timeout):
        raise SystemExit(1)
    print("Atlas runtime converged after the successful one-shot wait race.")


if __name__ == "__main__":
    main()
