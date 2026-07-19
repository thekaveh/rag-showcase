#!/usr/bin/env python3
"""Read-only preflight for the RAG evaluation's Atlas-infra dependencies.

Confirms every service the evaluation matrix relies on is up and in order
*without* running any ingestion, approach evaluation, or LLM judge — a cheap
"would the eval work?" check instead of the expensive full re-evaluation.

Two phases:

  1. Config  — Atlas ``doctor`` (static manifest / compose / overlay-env /
     plugin-manifest / LiteLLM-model validation; no services required).
  2. Live    — read-only probes of each running dependency the RAG plugin
     declares in ``backend_plugins/rag/plugin.yml``: LiteLLM aliases, Weaviate
     readiness + the ingested collections, LightRAG, the TEI reranker, and n8n.
     The probes run *inside* the backend container so they use the exact
     in-network endpoints and credentials the evaluation itself uses.

Exit code is 0 iff every checked item passes.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# The services the evaluation reaches through the backend, in the order the
# report lists them. Kept aligned with backend_plugins/rag/plugin.yml (see
# tests/test_eval_preflight.py::test_probe_covers_every_declared_dependency).
DECLARED_SERVICES = ("litellm", "weaviate", "lightrag", "tei-reranker", "n8n", "ollama")


def load_expected_aliases(manifest: Path | None = None) -> list[str]:
    """Return the LiteLLM alias names Atlas compiles from the consumer manifest.

    This is the ground truth for what ``/v1/models`` should expose, so a missing
    alias means the eval cannot route that approach/flavor.
    """
    manifest = manifest or (ROOT / "atlas.consumer.yml")
    data = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    models = (data.get("litellm_models") or {}).get("models") or []
    return sorted(row["name"] for row in models)


def load_expected_models(env_user: Path | None = None) -> list[str]:
    """Return the Ollama models the eval needs — the ``*_MODEL`` role vars in the
    consumer env file (embedding, LightRAG roles, Ragas). Under ``ollama-localhost``
    Atlas does not pull these, so a missing one means the eval will fail on first use.
    """
    env_user = env_user or (ROOT / "config" / "atlas.env.user")
    models: set[str] = set()
    for line in env_user.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        if key.endswith("_MODEL") and val:
            models.add(val)
    return sorted(models)


def envval(key: str, env_path: Path | None = None) -> str | None:
    """Read a key from Atlas's generated infra/.env (last assignment wins)."""
    env_path = env_path or (ROOT / "infra" / ".env")
    if not env_path.exists():
        return None
    value: str | None = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            value = line.split("=", 1)[1]
    return value


# Runs inside the backend container. Reads the plugin's own env-configured
# endpoints (plugin.yml + the compose overlay), probes each dependency read-only,
# and prints one JSON object. Every check is isolated so one failure never masks
# the others. httpx ships in the backend image (the RAG plugin imports it).
PROBE_SOURCE = r"""
import json, os, urllib.parse
import httpx

TIMEOUT = float(os.environ.get("PREFLIGHT_TIMEOUT", "10"))
results = {}


def record(name, fn):
    try:
        results[name] = {"ok": True, "detail": fn()}
    except Exception as exc:  # noqa: BLE001 - report, never abort siblings
        results[name] = {"ok": False, "detail": f"{type(exc).__name__}: {exc}"[:200]}


def litellm():
    base = os.environ["LITELLM_BASE_URL"].rstrip("/")
    key = os.environ.get("LITELLM_API_KEY", "")
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    r = httpx.get(f"{base}/v1/models", headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    ids = {m.get("id") for m in r.json().get("data", [])}
    expected = set(json.loads(os.environ.get("EXPECTED_ALIASES", "[]")))
    missing = sorted(expected - ids)
    if missing:
        raise RuntimeError(f"{len(missing)} alias(es) missing from /v1/models: {missing}")
    return f"reachable; all {len(expected)} declared aliases present"


def weaviate():
    base = os.environ["WEAVIATE_URL"].rstrip("/")
    httpx.get(f"{base}/v1/.well-known/ready", timeout=TIMEOUT).raise_for_status()
    schema = httpx.get(f"{base}/v1/schema", timeout=TIMEOUT)
    schema.raise_for_status()
    classes = {c.get("class") for c in schema.json().get("classes", [])}
    want = [
        os.environ.get("RAG_BASE_COLLECTION", ""),
        os.environ.get("RAG_CONTEXTUAL_COLLECTION", ""),
    ]
    missing = [c for c in want if c and c not in classes]
    if missing:
        raise RuntimeError(f"ready, but ingested collection(s) absent: {missing}")
    return f"ready; collections present: {[c for c in want if c]}"


def lightrag():
    base = os.environ["LIGHTRAG_ENDPOINT"].rstrip("/")
    key = os.environ.get("LIGHTRAG_API_KEY", "")
    headers = {"X-API-Key": key} if key else {}
    r = httpx.get(f"{base}/health", headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    return "healthy"


def tei_reranker():
    base = os.environ["TEI_RERANKER_ENDPOINT"].rstrip("/")
    httpx.get(f"{base}/health", timeout=TIMEOUT).raise_for_status()
    return "healthy"


def n8n():
    webhook = os.environ["N8N_ADAPTIVE_WEBHOOK_URL"]
    parts = urllib.parse.urlsplit(webhook)
    base = f"{parts.scheme}://{parts.netloc}"
    r = httpx.get(f"{base}/healthz", timeout=TIMEOUT)
    r.raise_for_status()
    return "healthy (webhook activation is verified separately by a real POST)"


def ollama():
    # Read-only: list already-pulled models via GET /api/tags — never the pull or
    # generate endpoints. Under ollama-localhost Atlas does not provision models, so
    # this confirms the host has them without any download or generation.
    # OLLAMA_ENDPOINT resolves per LLM_PROVIDER_SOURCE.
    endpoint = (os.environ.get("OLLAMA_ENDPOINT") or "").rstrip("/")
    if not endpoint:
        return "skipped — OLLAMA_ENDPOINT unresolved (non-ollama source or stack not fully started)"
    r = httpx.get(f"{endpoint}/api/tags", timeout=TIMEOUT)
    r.raise_for_status()
    tags = {m.get("name", "") for m in r.json().get("models", [])}
    want = json.loads(os.environ.get("EXPECTED_MODELS", "[]"))

    def present(model):
        if model in tags or f"{model}:latest" in tags:
            return True
        base = model.split(":")[0]
        return ":" not in model and any(t.split(":")[0] == base for t in tags)

    missing = [m for m in want if not present(m)]
    if missing:
        raise RuntimeError(f"model(s) not pulled: {missing} — for ollama-localhost run `ollama pull <name>`")
    return f"reachable; all {len(want)} required models pulled"


record("litellm", litellm)
record("weaviate", weaviate)
record("lightrag", lightrag)
record("tei-reranker", tei_reranker)
record("n8n", n8n)
record("ollama", ollama)
print(json.dumps(results))
"""


def run_doctor(project: str, base_port: str, timeout: float) -> dict:
    """Run Atlas's static consumer preflight (no services started)."""
    manifest = os.environ.get("ATLAS_CONSUMER_MANIFEST", str(ROOT / "atlas.consumer.yml"))
    cmd = [
        "./start.sh", "--consumer", manifest,
        "--project", project, "--base-port", base_port,
        "doctor", "--format", "json",
    ]
    try:
        proc = subprocess.run(
            cmd, cwd=ROOT / "infra", capture_output=True, text=True, timeout=timeout,
        )
    except FileNotFoundError:
        return {"ok": False, "detail": "infra/start.sh not found (submodule checked out?)"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "detail": f"doctor timed out after {timeout:.0f}s"}
    if proc.returncode == 0:
        return {"ok": True, "detail": "manifest / compose / overlay-env / plugin / model checks passed"}
    detail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return {"ok": False, "detail": detail[-1] if detail else f"exit {proc.returncode}"}


def _backend_running(container: str) -> bool:
    proc = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Running}}", container],
        capture_output=True, text=True,
    )
    return proc.returncode == 0 and proc.stdout.strip() == "true"


def run_live_probes(
    project: str,
    expected_aliases: list[str],
    expected_models: list[str],
    ollama_endpoint: str,
    timeout: float,
) -> dict:
    """Probe each running dependency read-only, from inside the backend."""
    container = f"{project}-backend"
    if subprocess.run(["docker", "version"], capture_output=True).returncode != 0:
        return {s: {"ok": False, "detail": "docker unavailable"} for s in DECLARED_SERVICES}
    if not _backend_running(container):
        return {
            s: {"ok": False, "detail": f"{container} is not running — start the stack first"}
            for s in DECLARED_SERVICES
        }
    proc = subprocess.run(
        [
            "docker", "exec", "-i",
            "-e", "PYTHONPATH=/app/plugins",
            "-e", f"EXPECTED_ALIASES={json.dumps(expected_aliases)}",
            "-e", f"EXPECTED_MODELS={json.dumps(expected_models)}",
            "-e", f"OLLAMA_ENDPOINT={ollama_endpoint}",
            "-e", f"PREFLIGHT_TIMEOUT={timeout}",
            container, "python", "-",
        ],
        input=PROBE_SOURCE, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "probe failed").strip().splitlines()
        return {s: {"ok": False, "detail": detail[-1] if detail else "probe failed"}
                for s in DECLARED_SERVICES}
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {s: {"ok": False, "detail": "unparseable probe output"} for s in DECLARED_SERVICES}


def overall_ok(config: dict | None, probes: dict) -> bool:
    ok = all(r.get("ok") for r in probes.values()) and bool(probes)
    if config is not None:
        ok = ok and config.get("ok", False)
    return ok


def format_report(config: dict | None, probes: dict) -> str:
    rows: list[tuple[str, str, bool, str]] = []
    if config is not None:
        rows.append(("config", "atlas doctor", config.get("ok", False), config.get("detail", "")))
    for name in DECLARED_SERVICES:
        r = probes.get(name, {"ok": False, "detail": "not probed"})
        rows.append(("live", name, r.get("ok", False), r.get("detail", "")))
    width = max((len(n) for _, n, _, _ in rows), default=7)
    lines = ["RAG evaluation preflight — read-only dependency check", ""]
    for phase, name, ok, detail in rows:
        mark = "✓" if ok else "✗"
        lines.append(f"  [{phase:<6}] {mark} {name.ljust(width)}  {detail}")
    lines.append("")
    lines.append("RESULT: " + ("all dependencies ready ✓" if overall_ok(config, probes)
                               else "one or more checks FAILED ✗"))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--format", choices=("table", "json"), default="table")
    parser.add_argument("--skip-doctor", action="store_true", help="Skip the Atlas static config phase")
    parser.add_argument("--project", default=os.environ.get("RAG_SHOWCASE_PROJECT_NAME", "rag-showcase"))
    parser.add_argument("--timeout", type=float, default=10.0, help="Per-probe timeout in seconds")
    args = parser.parse_args(argv)

    project = envval("PROJECT_NAME") or args.project
    base_port = os.environ.get("RAG_SHOWCASE_BASE_PORT", "auto")

    config = None if args.skip_doctor else run_doctor(project, base_port, timeout=max(args.timeout, 60.0))
    probes = run_live_probes(
        project,
        load_expected_aliases(),
        load_expected_models(),
        envval("OLLAMA_ENDPOINT") or "",
        timeout=args.timeout,
    )

    if args.format == "json":
        print(json.dumps({"config": config, "live": probes}, indent=2))
    else:
        print(format_report(config, probes))
    return 0 if overall_ok(config, probes) else 1


if __name__ == "__main__":
    sys.exit(main())
