"""Idempotently register the showcase RAG approaches (and their flavor aliases) as LiteLLM models.

Uses LiteLLM's admin API (STORE_MODEL_IN_DB=True in Atlas), so registrations
persist and survive restarts. Re-running deletes our existing rows first, so
it is safe to call on every startup.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Make the plugin package importable when run as a host script (in-container the
# seam provides PYTHONPATH=/app/plugins) — otherwise even --help dies on the
# import below. Mirrors ingest/ingest.py.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend_plugins"))

from rag.common import flavors  # noqa: E402

_NAMES = ["vanilla-rag", "hybrid-rag", "contextual-rag",
          "graph-rag", "agentic-rag", "n8n-adaptive-rag"]


def _model_spec(name: str, base: str | None = None, description: str | None = None) -> dict:
    base = base or name
    # api_key is injected at run() time (read from env then), not at import,
    # so a spec built at import never captures a stale/missing key.
    return {
        "model_name": name,
        "litellm_params": {
            "model": f"openai/{name}",
            "api_base": f"http://backend:8000/{base}/v1",
        },
        "model_info": {"description": description or f"RAG showcase: {name}"},
    }


def _model_specs() -> list[dict]:
    specs: list[dict] = []
    seen: set[str] = set()
    for base in _NAMES:
        for alias in flavors.aliases_for_base(base):
            if alias in seen:
                continue
            profile = flavors.get(alias)
            label = profile.label if profile.alias != profile.base else profile.alias
            specs.append(
                _model_spec(
                    profile.alias,
                    profile.base,
                    f"RAG showcase: {label} ({profile.base})",
                )
            )
            seen.add(alias)
    return specs


def _base() -> str:
    return os.environ.get("LITELLM_BASE_URL", "http://litellm:4000").rstrip("/")


def _key() -> str:
    # In the backend container the master key is exposed as LITELLM_API_KEY;
    # on a host run it's LITELLM_MASTER_KEY. Accept either.
    return (os.environ.get("LITELLM_MASTER_KEY")
            or os.environ.get("LITELLM_API_KEY") or "sk-noauth")


def _headers() -> dict:
    return {"Authorization": f"Bearer {_key()}"}


async def run() -> None:
    specs = _model_specs()
    async with httpx.AsyncClient(timeout=30.0) as client:
        info = await client.get(f"{_base()}/model/info", headers=_headers())
        info.raise_for_status()
        existing = info.json().get("data", [])
        ours = {m["model_name"] for m in specs}
        for row in existing:
            if row.get("model_name") in ours:
                mid = (row.get("model_info") or {}).get("id")
                if mid:
                    # the model provably exists (we just listed it), so a
                    # failed delete is a real error worth surfacing.
                    dresp = await client.post(f"{_base()}/model/delete",
                                              headers=_headers(), json={"id": mid})
                    dresp.raise_for_status()
        key = _key()
        for spec in specs:
            payload = {**spec, "litellm_params":
                       {**spec["litellm_params"], "api_key": key}}
            resp = await client.post(f"{_base()}/model/new",
                                     headers=_headers(), json=payload)
            resp.raise_for_status()
            print(f"  ↳ registered {spec['model_name']}")


if __name__ == "__main__":
    import argparse

    # Zero-option parser: makes --help safe (it used to attempt a live registration)
    # and rejects stray arguments.
    argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Configured via env vars: LITELLM_BASE_URL, LITELLM_MASTER_KEY or "
               "LITELLM_API_KEY.",
    ).parse_args()
    asyncio.run(run())
