#!/usr/bin/env python3
"""Run the demo query matrix: every demo query x every RAG approach, through the
stack's LiteLLM gateway, capturing answer + retrieved sources + server metrics +
client-side latency. Writes compare/results/matrix.json by default.

Host-run. Reads LITELLM_PORT + LITELLM_MASTER_KEY from infra/.env (the host-
published gateway; the in-repo tests' localhost:4000 default is LiteLLM's
container-internal port, reachable in-network as litellm:4000 but not published on
the host at 4000). Per-cell try/except so one slow/failed approach is recorded,
not fatal.

    uv run python compare/run_matrix.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from compare import flavors as flavor_config  # noqa: E402

RESULTS = ROOT / "compare" / "results"
# The six base approaches ("models" because that is the OpenAI-API field name at the
# gateway boundary). Derived, not copied — compare/flavors.py owns the display order.
ALL_MODELS = list(flavor_config.BASE_APPROACHES)

# build_response() renders: answer + optional "<details>…Retrieved context…</details>"
# + "\n\n---\n📊 {s}s · {n} chunks · {n} LLM calls · {n} cloud". Parse that back.
_FOOTER = re.compile(
    r"📊\s*([\d.]+)s\s*·\s*(\d+)\s*chunks?\s*·\s*(\d+)\s*LLM calls?\s*·\s*(\d+)\s*cloud")
_SRC_TITLE = re.compile(r"\*\*(\d+)\.\s*(.+?)\*\*(?:\s*·\s*score\s*([\d.]+))?")
_SRC_MARK = "<details><summary>🔎 Retrieved context"


def envval(key: str, default: str = "") -> str:
    env = ROOT / "infra" / ".env"
    val = default
    if env.is_file():
        for line in env.read_text(encoding="utf-8").splitlines():
            if line.startswith(key + "="):
                val = line.split("=", 1)[1].strip()  # last assignment wins
    return val


def queries_file() -> Path:
    return Path(os.environ.get("MATRIX_QUERIES_FILE", "demo/queries.yaml"))


def results_file() -> Path:
    return RESULTS / os.environ.get("MATRIX_RESULTS_FILE", "matrix.json")


def _csv_env(name: str) -> list[str]:
    return [m.strip() for m in os.environ.get(name, "").split(",") if m.strip()]


def flavors_file() -> Path:
    return Path(os.environ.get("MATRIX_FLAVORS_FILE", str(flavor_config.DEFAULT_MANIFEST)))


def selected_profiles() -> list[flavor_config.FlavorProfile]:
    if models := _csv_env("MATRIX_MODELS"):
        return [flavor_config.profile_for_model(model, manifest=flavors_file()) for model in models]
    if selection := _csv_env("MATRIX_FLAVORS"):
        return flavor_config.expand_selection(selection, manifest=flavors_file())
    return [flavor_config.profile_for_model(model, manifest=flavors_file()) for model in ALL_MODELS]


def parse_content(content: str) -> dict:
    """Split a uniform build_response payload into answer / sources / metrics.

    Wrapper approaches (n8n-adaptive-rag) pass the routed approach's fully
    rendered payload through as their answer, nesting a second footer and
    sources block. So: metrics come from the LAST footer (the wrapper's own
    numbers, not the inner approach's), the answer truncates at the FIRST
    footer/details (where nested rendering starts), and sources are scanned
    from the first details block to the end so both the inner retrieval block
    and the wrapper's route block are captured.
    """
    footers = list(_FOOTER.finditer(content))
    metrics = None
    body = content
    if footers:
        last = footers[-1]
        metrics = {"seconds": float(last.group(1)), "chunks": int(last.group(2)),
                   "llm_calls": int(last.group(3)), "cloud_calls": int(last.group(4))}
        body = content[:footers[0].start()].rstrip("\n").rstrip("-").rstrip("\n")
    answer = body
    idx = body.find(_SRC_MARK)
    if idx != -1:
        answer = body[:idx].rstrip()
    sidx = content.find(_SRC_MARK)
    sources_raw = content[sidx:] if sidx != -1 else ""
    sources = [{"title": t.strip(), "score": float(s) if s else None}
               for _, t, s in _SRC_TITLE.findall(sources_raw)]
    return {"answer": answer.strip(), "sources": sources, "metrics": metrics}


def main() -> None:
    port, key = envval("LITELLM_PORT"), envval("LITELLM_MASTER_KEY")
    if not port or not key:
        # Without these the run would grind through every cell against
        # "http://localhost:" and exit 0 with a 100%-error matrix.
        raise SystemExit("LITELLM_PORT / LITELLM_MASTER_KEY not found in infra/.env — "
                         "run scripts/start-all.sh (or scripts/setup-overlay.sh) first")
    base = f"http://localhost:{port}"
    query_path = ROOT / queries_file()
    queries = yaml.safe_load(query_path.read_text(encoding="utf-8")) or []
    if not queries:
        raise SystemExit(f"{query_path}: no query rows")
    # Validate rows up front: a malformed row discovered mid-run used to abort the
    # matrix after real cells were already paid for, losing all of them.
    bad = [i for i, q in enumerate(queries)
           if not (isinstance(q, dict) and q.get("id") and q.get("query"))]
    if bad:
        raise SystemExit(f"{query_path}: query rows missing id/query at indices {bad}")
    profiles = selected_profiles()
    RESULTS.mkdir(parents=True, exist_ok=True)
    out: dict = {"base": base, "models": [p.alias for p in profiles],
                 "model_profiles": [
                     {
                         "model": p.alias,
                         "base_model": p.base,
                         "flavor": p.flavor,
                         "requires_reingest": p.requires_reingest,
                     }
                     for p in profiles
                 ],
                 "queries_file": str(queries_file()),
                 "queries": [{k: q.get(k) for k in ("id", "query", "expect_winner", "rationale")}
                             for q in queries],
                 "cells": []}
    print(f"matrix: {len(queries)} queries x {len(profiles)} approaches/flavors @ {base}")
    with httpx.Client(timeout=httpx.Timeout(420.0, connect=10.0)) as client:
        for q in queries:
            for profile in profiles:
                model = profile.alias
                t0 = time.monotonic()
                cell = {
                    "query_id": q["id"],
                    "model": model,
                    "base_model": profile.base,
                    "flavor": profile.flavor,
                    "requires_reingest": profile.requires_reingest,
                }
                try:
                    r = client.post(f"{base}/v1/chat/completions",
                                    headers={"Authorization": f"Bearer {key}"},
                                    json={"model": model,
                                          "messages": [{"role": "user", "content": q["query"]}]})
                    dt = time.monotonic() - t0
                    r.raise_for_status()
                    content = r.json()["choices"][0]["message"]["content"]
                    cell.update({"ok": True, "latency_s": round(dt, 1),
                                 "raw": content, **parse_content(content)})
                except Exception as e:  # noqa: BLE001 — record, don't abort the run
                    cell.update({"ok": False, "latency_s": round(time.monotonic() - t0, 1),
                                 "error": f"{type(e).__name__}: {e}"})
                out["cells"].append(cell)
                tag = "ok " if cell.get("ok") else "ERR"
                ans = (cell.get("answer") or cell.get("error") or "")[:60].replace("\n", " ")
                print(f"  [{tag}] {q['id']:14} {model:18} {cell['latency_s']:6}s  {ans}", flush=True)
    output = results_file()
    output.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {output} ({len(out['cells'])} cells)")


if __name__ == "__main__":
    import argparse

    # Zero-option parser: config is env-var-only, but this makes --help safe (it used
    # to start a real matrix run and overwrite results) and rejects stray arguments.
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Configured via env vars: MATRIX_QUERIES_FILE, MATRIX_RESULTS_FILE, "
               "MATRIX_MODELS, MATRIX_FLAVORS, MATRIX_FLAVORS_FILE.",
    ).parse_args()
    main()
