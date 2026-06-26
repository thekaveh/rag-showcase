"""Idempotently register the six showcase approaches as LiteLLM models.

Uses LiteLLM's admin API (STORE_MODEL_IN_DB=True in Atlas), so registrations
persist and survive restarts. Re-running deletes our existing rows first, so
it is safe to call on every startup.
"""
from __future__ import annotations

import asyncio
import os

import httpx

_NAMES = ["vanilla-rag", "hybrid-rag", "contextual-rag",
          "graph-rag", "agentic-rag", "n8n-adaptive-rag"]


def _model_spec(name: str) -> dict:
    return {
        "model_name": name,
        "litellm_params": {
            "model": f"openai/{name}",
            "api_base": f"http://backend:8000/{name}/v1",
            # any non-empty key; the backend route doesn't check it
            "api_key": os.environ.get("LITELLM_MASTER_KEY", "sk-noauth"),
        },
        "model_info": {"description": f"RAG showcase: {name}"},
    }


MODELS = [_model_spec(n) for n in _NAMES]


def _base() -> str:
    return os.environ.get("LITELLM_BASE_URL", "http://litellm:4000").rstrip("/")


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ.get('LITELLM_MASTER_KEY','')}"}


async def run() -> None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        info = await client.get(f"{_base()}/model/info", headers=_headers())
        info.raise_for_status()
        existing = info.json().get("data", [])
        ours = {m["model_name"] for m in MODELS}
        for row in existing:
            if row.get("model_name") in ours:
                mid = (row.get("model_info") or {}).get("id")
                if mid:
                    await client.post(f"{_base()}/model/delete",
                                      headers=_headers(), json={"id": mid})
        for spec in MODELS:
            resp = await client.post(f"{_base()}/model/new",
                                     headers=_headers(), json=spec)
            resp.raise_for_status()
            print(f"  ↳ registered {spec['model_name']}")


if __name__ == "__main__":
    asyncio.run(run())
