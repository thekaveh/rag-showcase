#!/usr/bin/env python3
"""Run the demo query matrix: every demo query x every RAG approach, through the
stack's LiteLLM gateway, capturing answer + retrieved sources + server metrics +
client-side latency. Writes compare/results/matrix.json.

Host-run. Reads LITELLM_PORT + LITELLM_MASTER_KEY from infra/.env (the published
gateway; the in-repo tests' localhost:4000 default is the in-network address, not
the published one). Per-cell try/except so one slow/failed approach is recorded,
not fatal.

    uv run python compare/run_matrix.py
"""
from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "compare" / "results"
_ALL = ["vanilla-rag", "hybrid-rag", "contextual-rag",
        "graph-rag", "agentic-rag", "n8n-adaptive-rag"]
# Default to all six; MATRIX_MODELS (comma-separated) overrides — e.g. to exclude an
# approach whose backend isn't reliably available in a given run.
MODELS = [m.strip() for m in os.environ.get("MATRIX_MODELS", "").split(",") if m.strip()] or _ALL

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


def parse_content(content: str) -> dict:
    """Split a uniform build_response payload into answer / sources / metrics."""
    body = content
    metrics = None
    m = _FOOTER.search(content)
    if m:
        metrics = {"seconds": float(m.group(1)), "chunks": int(m.group(2)),
                   "llm_calls": int(m.group(3)), "cloud_calls": int(m.group(4))}
        body = content[:m.start()].rstrip("\n").rstrip("-").rstrip("\n")
    answer, sources_raw = body, ""
    idx = body.find(_SRC_MARK)
    if idx != -1:
        answer, sources_raw = body[:idx].rstrip(), body[idx:]
    sources = [{"title": t.strip(), "score": float(s) if s else None}
               for _, t, s in _SRC_TITLE.findall(sources_raw)]
    return {"answer": answer.strip(), "sources": sources, "metrics": metrics}


def main() -> None:
    port, key = envval("LITELLM_PORT"), envval("LITELLM_MASTER_KEY")
    base = f"http://localhost:{port}"
    queries = yaml.safe_load((ROOT / "demo" / "queries.yaml").read_text(encoding="utf-8"))
    RESULTS.mkdir(parents=True, exist_ok=True)
    out: dict = {"base": base, "models": MODELS,
                 "queries": [{k: q.get(k) for k in ("id", "query", "expect_winner", "rationale")}
                             for q in queries],
                 "cells": []}
    print(f"matrix: {len(queries)} queries x {len(MODELS)} approaches @ {base}")
    with httpx.Client(timeout=httpx.Timeout(420.0, connect=10.0)) as client:
        for q in queries:
            for model in MODELS:
                t0 = time.monotonic()
                cell = {"query_id": q["id"], "model": model}
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
    (RESULTS / "matrix.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {RESULTS / 'matrix.json'} ({len(out['cells'])} cells)")


if __name__ == "__main__":
    main()
