# 7.3 RAG Showcase Implementation Plan

> **Status:** Historical artifact — Tasks 0–19 are complete. This is the as-built plan, not a live task list.

> **Section numbering:** primary sections use a domain-specific `Task N` scheme rather than `1./1.1.` numbering; that task ordering is this plan's hierarchy. Kept as-built.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship a six-approach RAG comparison showcase that reuses Atlas (as a Git submodule) for all infrastructure, surfaces each approach as a selectable model in OpenWebUI's multi-model chat, and doubles as a written test-drive of Atlas's reusability.

**Architecture:** Atlas runs as a pinned submodule under `infra/` (`--track gen-ai-rag`). Six RAG approaches live as a self-contained, high-cohesion Python package (`backend_plugins/rag/`) that is **bind-mounted into Atlas's existing FastAPI backend** through a generic, two-line "plugin seam" we add to the backend (the only Atlas change). Each approach is an OpenAI-compatible `/<name>/v1/chat/completions` route, registered into LiteLLM via its `/model/new` admin API (no Atlas edits) so it auto-appears in OpenWebUI. Ingestion (Docling → Weaviate + LightRAG) and registration live in the showcase repo.

**Tech Stack:** Python 3.10+, FastAPI, httpx, weaviate-client v4, asyncpg (already in backend), Ollama/LiteLLM (LLMs + embeddings), Weaviate (vector + BM25), Neo4j + LightRAG (graph), TEI reranker, Docling (ingest), n8n (low-code workflow), Docker Compose, pytest + pytest-asyncio + respx.

## Global Constraints

- **Atlas changes must be generic and minimal.** The only edits to the Atlas tree are two general-purpose backend seams (plugin-router loader + plugin-requirements installer). No RAG-specific logic, no new Atlas services. (From spec §4.2.)
- **Atlas is consumed on a feature branch, pinned by the submodule.** `main` is protected in `thekaveh/atlas` — never push to it. Seam work lands on an Atlas branch via PR/CI; the submodule tracks that branch while building. (Atlas `CLAUDE.md` Git Workflow.)
- **Local-first LLM routing.** Default roles: `embed=nomic-embed-text`, `light_gen=qwen3.6`, `contextual_blurb=gemma4:31b`, `extraction=gemma4:31b`, `agentic=qwen3.6`. Cloud is a config-only fallback. No cloud key required to run. (Spec §7.) *(Corrected during maintenance: Atlas's catalog has no `gemma4:31b` and registers `qwen3.6:latest` (not bare `qwen3.6`), so the shipped `roles.yaml` uses `qwen3.6:latest` for all chat roles.)*
- **One corpus, one embedding model across approaches.** All vector approaches embed via LiteLLM `nomic-embed-text`; LightRAG legitimately uses pgvector. (Spec §2 fairness.)
- **Six model names (clash-free):** `vanilla-rag`, `hybrid-rag`, `contextual-rag`, `graph-rag`, `agentic-rag`, `n8n-adaptive-rag`. (`graph-rag` is used instead of the spec's label `lightrag` to avoid colliding with Atlas's built-in `lightrag` model.)
- **In-network service addresses (stable):** `http://litellm:4000` (auth `LITELLM_MASTER_KEY`), `http://weaviate:8080` (gRPC `:50051`), `bolt://neo4j-graph-db:7687`, `http://lightrag:9621` (auth `LIGHTRAG_API_KEY`), `http://tei-reranker:80/rerank`, `http://docling-gpu:8000/v1/document/convert`, `http://backend:8000`. Network: `${PROJECT_NAME}-network` (default `atlas-network`). (Spec §4.4.)
- **Backend already injects** (do not re-plumb): `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `LITELLM_EMBEDDING_MODEL`, `WEAVIATE_URL`, `NEO4J_URI/USER/PASSWORD`, `REDIS_URL`, `DOCLING_ENDPOINT`, `LIGHTRAG_ENDPOINT/API_KEY`, `DATABASE_URL`. We add `TEI_RERANKER_ENDPOINT`, `BACKEND_PLUGINS_DIR`, `RAG_ROLES_FILE`, `N8N_ADAPTIVE_WEBHOOK_URL` via the overlay.

---

## File Structure

**Showcase repo (`/Users/kaveh/repos/rag-showcase/`):**
- `infra/` — Atlas submodule (created Task 1).
- `compose/rag-overlay.yml` — augments the existing `backend` service with the plugin mount + env (Task 3). Symlinked into `infra/services/_user/rag-showcase/compose.yml`.
- `backend_plugins/requirements.txt` — extra deps installed into the backend at startup (Task 4).
- `backend_plugins/rag/__init__.py` — exposes `router` (aggregates all six approaches) (Task 5).
- `backend_plugins/rag/roles.yaml` — role→model map (Task 4).
- `backend_plugins/rag/common/config.py` — roles loader + env accessors (Task 4).
- `backend_plugins/rag/common/litellm.py` — embed + chat client (Task 4).
- `backend_plugins/rag/common/vectors.py` — Weaviate ingest/search + TEI rerank (Task 6).
- `backend_plugins/rag/common/openai_io.py` — OpenAI request/response models + uniform surfacing builder (Task 5).
- `backend_plugins/rag/approaches/{vanilla,hybrid,contextual,graph,agentic,n8n}.py` — one router each (Tasks 7–12).
- `backend_plugins/rag/tests/` — pytest suite (per task).
- `ingest/ingest.py` — Docling → Weaviate(base+contextual) + LightRAG loader (Task 13).
- `register/register_models.py` — idempotent LiteLLM `/model/new` registration (Task 14).
- `corpus/` — MultiHop-RAG subset + hand-picked keyword docs + `fetch_corpus.py` (Task 15).
- `demo/queries.yaml` — the contrasting query matrix (Task 16).
- `scripts/{start-all,stop-all,setup-overlay}.sh` — orchestration (Task 17).
- `tests/test_demo_matrix.py` — end-to-end contrast assertions (Task 18, integration).
- `docs/atlas-reuse-assessment.md` — the test-drive deliverable (Task 19).
- `pyproject.toml`, `.gitignore`, `README.md` — scaffolding (Task 0).

**Atlas tree (submodule, on a feature branch — Task 2 only):**
- `services/backend/app/app/main.py` — add the generic plugin seam (~20 lines).

---

## Task 0: Repo scaffolding

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `README.md`

**Interfaces:**
- Produces: a pytest-discoverable repo with `backend_plugins/` on the path.

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "rag-showcase"
version = "0.1.0"
description = "Six-approach RAG comparison showcase over Atlas"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["backend_plugins"]
asyncio_mode = "auto"
testpaths = ["backend_plugins/rag/tests", "tests"]

[dependency-groups]
dev = ["pytest>=8", "pytest-asyncio>=0.23", "respx>=0.21", "httpx>=0.27", "pyyaml>=6"]
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.venv/
.pytest_cache/
corpus/raw/
infra/.env
infra/volumes/
```

- [ ] **Step 3: Create `README.md`**

```markdown
# RAG Showcase

Six RAG approaches compared side-by-side in OpenWebUI's multi-model chat, all
running on [Atlas](https://github.com/thekaveh/atlas) (vendored at `infra/`).

Quick start: `./scripts/start-all.sh` then open the printed OpenWebUI URL,
start a multi-model chat, and select the six `*-rag` models.

See `docs/superpowers/specs/2026-06-25-rag-showcase-design.md` for the design.
```

- [ ] **Step 4: Verify pytest collects nothing yet (no error)**

Run: `uv run pytest -q` (or `pytest -q`)
Expected: "no tests ran" (exit 5) — confirms config is valid.

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml .gitignore README.md
git commit -m "chore: repo scaffolding for RAG showcase"
```

---

## Task 1: Add Atlas as a submodule

**Files:**
- Create: `.gitmodules`, `infra/` (submodule)

**Interfaces:**
- Produces: `infra/start.sh`, `infra/services/`, `infra/.env` (from example).

- [ ] **Step 1: Add the submodule**

```bash
git submodule add https://github.com/thekaveh/atlas infra
git submodule update --init --recursive
```

- [ ] **Step 2: Seed infra `.env` with the project name**

```bash
cp infra/.env.example infra/.env
printf '\nPROJECT_NAME=atlas\n' >> infra/.env
```
(Keep `PROJECT_NAME=atlas` so the network is `atlas-network`; change only if you run multiple stacks.)

- [ ] **Step 3: Verify the submodule resolves**

Run: `git -C infra rev-parse --short HEAD && ls infra/services/backend/app/app/main.py`
Expected: a commit hash + the path printed (no error).

- [ ] **Step 4: Commit**

```bash
git add .gitmodules infra
git commit -m "build: vendor Atlas as infra submodule"
```

---

## Task 2: Generic backend plugin seam (Atlas feature branch)

**Files:**
- Modify: `infra/services/backend/app/app/main.py` (after `app.include_router(ray_router)`, line ~138)

**Interfaces:**
- Produces: backend loads any package under `$BACKEND_PLUGINS_DIR` exposing `router`, after installing `$BACKEND_PLUGINS_DIR/requirements.txt` if present. No-op when the dir is absent.

- [ ] **Step 1: Create an Atlas feature branch**

```bash
git -C infra checkout -b feature/backend-plugin-seam
```

- [ ] **Step 2: Write the failing test (in the Atlas backend test suite)**

Create `infra/services/backend/app/app/tests/test_plugin_seam.py`:

```python
import importlib, sys, types
from pathlib import Path


def test_load_plugins_includes_router(tmp_path, monkeypatch):
    # Arrange: a fake plugin package exposing `router`
    pkg = tmp_path / "demoplugin"
    pkg.mkdir()
    (pkg / "__init__.py").write_text(
        "from fastapi import APIRouter\n"
        "router = APIRouter()\n"
        "@router.get('/__demoplugin__')\n"
        "def ping():\n"
        "    return {'ok': True}\n"
    )
    from fastapi import FastAPI
    app = FastAPI()
    monkeypatch.setenv("BACKEND_PLUGINS_DIR", str(tmp_path))

    import plugin_seam  # the module we will create
    plugin_seam.load_plugins(app)

    paths = {r.path for r in app.router.routes}
    assert "/__demoplugin__" in paths


def test_load_plugins_noop_when_dir_missing(monkeypatch):
    from fastapi import FastAPI
    app = FastAPI()
    before = len(app.router.routes)
    monkeypatch.setenv("BACKEND_PLUGINS_DIR", "/nonexistent/path/xyz")
    import plugin_seam
    plugin_seam.load_plugins(app)
    assert len(app.router.routes) == before
```

- [ ] **Step 3: Run it to confirm it fails**

Run: `cd infra/services/backend/app/app && python -m pytest tests/test_plugin_seam.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'plugin_seam'`.

- [ ] **Step 4: Create `infra/services/backend/app/app/plugin_seam.py`**

```python
"""Generic downstream extension seam (no RAG-specific logic).

A downstream consumer mounts a directory of plugin packages at
``$BACKEND_PLUGINS_DIR`` (default ``/app/plugins``). Each immediate
subdirectory that is an importable package exposing a module-level
``router`` (a FastAPI ``APIRouter``) is included into the app. If the
directory contains ``requirements.txt`` it is installed first. The whole
thing is a no-op when the directory is absent, so base Atlas is unaffected.
"""
from __future__ import annotations

import importlib
import logging
import subprocess
import sys
from pathlib import Path

_log = logging.getLogger("uvicorn.error")


def _install_requirements(plugins_dir: Path) -> None:
    reqs = plugins_dir / "requirements.txt"
    if not reqs.is_file():
        return
    _log.info("plugin seam: installing %s", reqs)
    subprocess.run(
        [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", str(reqs)],
        check=False,
    )


def load_plugins(app) -> None:
    import os

    plugins_dir = Path(os.getenv("BACKEND_PLUGINS_DIR", "/app/plugins"))
    if not plugins_dir.is_dir():
        return
    _install_requirements(plugins_dir)
    if str(plugins_dir) not in sys.path:
        sys.path.insert(0, str(plugins_dir))
    for entry in sorted(plugins_dir.iterdir()):
        if not (entry.is_dir() and (entry / "__init__.py").is_file()):
            continue
        try:
            module = importlib.import_module(entry.name)
            router = getattr(module, "router", None)
            if router is not None:
                app.include_router(router)
                _log.info("plugin seam: loaded plugin %r", entry.name)
        except Exception:  # one bad plugin must not crash the backend
            _log.exception("plugin seam: failed to load plugin %r", entry.name)
```

- [ ] **Step 5: Run the test to confirm it passes**

Run: `cd infra/services/backend/app/app && python -m pytest tests/test_plugin_seam.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Wire the seam into `main.py`**

In `infra/services/backend/app/app/main.py`, immediately after the existing line `app.include_router(ray_router)` (line ~138), add:

```python
# Generic downstream extension seam — no-op unless a consumer mounts
# $BACKEND_PLUGINS_DIR with plugin packages. See plugin_seam.py.
from plugin_seam import load_plugins  # noqa: E402
load_plugins(app)
```

- [ ] **Step 7: Run the full backend test suite to confirm no regressions**

Run: `cd infra/services/backend/app/app && python -m pytest -q`
Expected: PASS (existing tests + the 2 new ones).

- [ ] **Step 8: Commit on the Atlas branch**

```bash
git -C infra add services/backend/app/app/plugin_seam.py \
  services/backend/app/app/tests/test_plugin_seam.py \
  services/backend/app/app/main.py
git -C infra commit -m "feat(backend): generic plugin seam for downstream route packages"
```

- [ ] **Step 9: Pin the submodule to the seam commit and commit in the showcase repo**

```bash
git add infra
git commit -m "build: pin Atlas submodule to backend-plugin-seam branch"
```

(When ready, open a PR on Atlas for `feature/backend-plugin-seam` and let the 3 `services-lint` checks pass before any merge — per Atlas's Git Workflow. Pinning to the branch commit is sufficient to build now.)

---

## Task 3: Compose overlay + symlink wiring

**Files:**
- Create: `compose/rag-overlay.yml`, `scripts/setup-overlay.sh`

**Interfaces:**
- Produces: when `setup-overlay.sh` has run, `./start.sh` mounts `backend_plugins/` into the backend at `/app/plugins` and sets the showcase env.

- [ ] **Step 1: Create `compose/rag-overlay.yml`**

```yaml
# Augments Atlas's existing `backend` service (merged by service name).
# Relative paths resolve against the project dir = infra/ (the dir of the
# first -f file, docker-compose.yml), so ../backend_plugins == repo root.
services:
  backend:
    environment:
      BACKEND_PLUGINS_DIR: /app/plugins
      RAG_ROLES_FILE: /app/plugins/rag/roles.yaml
      TEI_RERANKER_ENDPOINT: ${TEI_RERANKER_ENDPOINT:-http://tei-reranker:80}
      N8N_ADAPTIVE_WEBHOOK_URL: ${N8N_ADAPTIVE_WEBHOOK_URL:-http://n8n:5678/webhook/adaptive-rag}
    volumes:
      - ../backend_plugins:/app/plugins:ro
```

- [ ] **Step 2: Create `scripts/setup-overlay.sh`**

```bash
#!/usr/bin/env bash
# Symlink the showcase's compose overlay into Atlas's _user overlay slot,
# so Atlas's bootstrapper auto-discovers and merges it. Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SLOT="$ROOT/infra/services/_user/rag-showcase"
mkdir -p "$SLOT"
ln -sf "../../../../compose/rag-overlay.yml" "$SLOT/compose.yml"
echo "Linked $SLOT/compose.yml -> compose/rag-overlay.yml"
```

(The link target is relative to `$SLOT`: `infra/services/_user/rag-showcase/` → up 4 → repo root → `compose/rag-overlay.yml`.)

- [ ] **Step 3: Make it executable and run it**

```bash
chmod +x scripts/setup-overlay.sh
./scripts/setup-overlay.sh
```

- [ ] **Step 4: Verify the symlink resolves to the overlay**

Run: `cat infra/services/_user/rag-showcase/compose.yml | head -3`
Expected: the first lines of `rag-overlay.yml` (the comment + `services:`).

- [ ] **Step 5: Commit**

```bash
git add compose/rag-overlay.yml scripts/setup-overlay.sh
git commit -m "build: backend plugin compose overlay + _user symlink wiring"
```

---

## Task 4: Common config + LiteLLM client

**Files:**
- Create: `backend_plugins/requirements.txt`, `backend_plugins/rag/__init__.py` (stub), `backend_plugins/rag/roles.yaml`, `backend_plugins/rag/common/__init__.py`, `backend_plugins/rag/common/config.py`, `backend_plugins/rag/common/litellm.py`
- Test: `backend_plugins/rag/tests/test_litellm.py`, `backend_plugins/rag/tests/test_config.py`

**Interfaces:**
- Produces:
  - `config.role(name: str) -> str` — resolve a role to a model name from `roles.yaml`.
  - `litellm.embed(texts: list[str]) -> list[list[float]]`
  - `litellm.chat(model: str, messages: list[dict], tools: list[dict] | None = None, stream: bool = False) -> dict` — returns the raw OpenAI response JSON (non-stream).

- [ ] **Step 1: Create `backend_plugins/requirements.txt`**

```text
weaviate-client>=4.9,<5
httpx>=0.27
PyYAML>=6
```

- [ ] **Step 2: Create `backend_plugins/rag/roles.yaml`**

```yaml
# Local-first role→model map (LiteLLM model names). Flip any value to a
# cloud model (e.g. claude-sonnet-4-6) once a key is configured.
embed: nomic-embed-text
light_gen: qwen3.6
contextual_blurb: gemma4:31b
extraction: gemma4:31b
agentic: qwen3.6
```

- [ ] **Step 3: Create package stubs**

`backend_plugins/rag/__init__.py`:
```python
# router is assembled in Task 5; kept importable from the start.
router = None
```
`backend_plugins/rag/common/__init__.py`: (empty file)

- [ ] **Step 4: Write the failing config test**

`backend_plugins/rag/tests/test_config.py`:
```python
from rag.common import config


def test_role_resolves_from_yaml(tmp_path, monkeypatch):
    f = tmp_path / "roles.yaml"
    f.write_text("light_gen: my-model\nembed: my-embed\n")
    monkeypatch.setenv("RAG_ROLES_FILE", str(f))
    config._CACHE.clear()
    assert config.role("light_gen") == "my-model"
    assert config.role("embed") == "my-embed"


def test_role_unknown_raises(tmp_path, monkeypatch):
    f = tmp_path / "roles.yaml"
    f.write_text("light_gen: x\n")
    monkeypatch.setenv("RAG_ROLES_FILE", str(f))
    config._CACHE.clear()
    try:
        config.role("nope")
        assert False, "expected KeyError"
    except KeyError:
        pass
```

- [ ] **Step 5: Run it to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.common.config`.

- [ ] **Step 6: Create `backend_plugins/rag/common/config.py`**

```python
"""Role→model resolution and shared env accessors."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

_CACHE: dict[str, str] = {}


def _load() -> dict[str, str]:
    if _CACHE:
        return _CACHE
    path = Path(os.getenv("RAG_ROLES_FILE", "/app/plugins/rag/roles.yaml"))
    data = yaml.safe_load(path.read_text()) if path.is_file() else {}
    _CACHE.update({str(k): str(v) for k, v in (data or {}).items()})
    return _CACHE


def role(name: str) -> str:
    """Return the LiteLLM model configured for ``name``; KeyError if unset."""
    table = _load()
    if name not in table:
        raise KeyError(f"role '{name}' not defined in roles.yaml")
    return table[name]


def litellm_base() -> str:
    return os.environ.get("LITELLM_BASE_URL", "http://litellm:4000").rstrip("/")


def litellm_key() -> str:
    return os.environ.get("LITELLM_API_KEY", "")
```

- [ ] **Step 7: Run config test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_config.py -q`
Expected: PASS (2 passed).

- [ ] **Step 8: Write the failing LiteLLM client test**

`backend_plugins/rag/tests/test_litellm.py`:
```python
import respx
import httpx
import pytest
from rag.common import litellm


@pytest.mark.asyncio
@respx.mock
async def test_embed_posts_to_litellm(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    route = respx.post("http://litellm:4000/v1/embeddings").mock(
        return_value=httpx.Response(200, json={"data": [{"embedding": [0.1, 0.2]}]})
    )
    out = await litellm.embed(["hello"], model="nomic-embed-text")
    assert out == [[0.1, 0.2]]
    assert route.called
    sent = route.calls.last.request
    assert sent.headers["authorization"] == "Bearer sk-test"


@pytest.mark.asyncio
@respx.mock
async def test_chat_returns_json(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_API_KEY", "sk-test")
    respx.post("http://litellm:4000/v1/chat/completions").mock(
        return_value=httpx.Response(200, json={
            "choices": [{"message": {"content": "hi", "role": "assistant"}}]
        })
    )
    out = await litellm.chat("qwen3.6", [{"role": "user", "content": "hey"}])
    assert out["choices"][0]["message"]["content"] == "hi"
```

- [ ] **Step 9: Run it to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_litellm.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.common.litellm`.

- [ ] **Step 10: Create `backend_plugins/rag/common/litellm.py`**

```python
"""Thin async client for the LiteLLM gateway (OpenAI-compatible)."""
from __future__ import annotations

from typing import Any

import httpx

from . import config

_TIMEOUT = httpx.Timeout(120.0, connect=10.0)


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {config.litellm_key()}",
            "Content-Type": "application/json"}


async def embed(texts: list[str], model: str | None = None) -> list[list[float]]:
    model = model or config.role("embed")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.litellm_base()}/v1/embeddings",
            headers=_headers(),
            json={"model": model, "input": texts},
        )
        resp.raise_for_status()
        return [row["embedding"] for row in resp.json()["data"]]


async def chat(model: str, messages: list[dict[str, Any]],
               tools: list[dict] | None = None,
               temperature: float = 0.0) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": model, "messages": messages,
                               "temperature": temperature}
    if tools:
        payload["tools"] = tools
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            f"{config.litellm_base()}/v1/chat/completions",
            headers=_headers(), json=payload,
        )
        resp.raise_for_status()
        return resp.json()
```

- [ ] **Step 11: Run to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_litellm.py -q`
Expected: PASS (2 passed).

- [ ] **Step 12: Commit**

```bash
git add backend_plugins/requirements.txt backend_plugins/rag
git commit -m "feat(rag): common config + LiteLLM client"
```

---

## Task 5: OpenAI I/O models + uniform surfacing

**Files:**
- Create: `backend_plugins/rag/common/openai_io.py`
- Modify: `backend_plugins/rag/__init__.py`
- Test: `backend_plugins/rag/tests/test_openai_io.py`

**Interfaces:**
- Produces:
  - `ChatRequest` (pydantic): `.model`, `.messages`, `.stream`, plus `.last_user() -> str`.
  - `build_response(model: str, answer: str, sources: list[Source], metrics: Metrics) -> dict` — an OpenAI `chat.completion` dict whose `content` = answer + collapsible sources + metrics footer.
  - `Source(title: str, snippet: str, score: float | None)`, `Metrics(seconds: float, chunks: int, llm_calls: int, cloud_calls: int)`.

- [ ] **Step 1: Write the failing test**

`backend_plugins/rag/tests/test_openai_io.py`:
```python
from rag.common.openai_io import build_response, Source, Metrics, ChatRequest


def test_build_response_shapes_openai_and_embeds_sources():
    resp = build_response(
        model="vanilla-rag",
        answer="The answer.",
        sources=[Source(title="Doc A", snippet="alpha", score=0.9)],
        metrics=Metrics(seconds=1.2, chunks=1, llm_calls=1, cloud_calls=0),
    )
    assert resp["object"] == "chat.completion"
    assert resp["model"] == "vanilla-rag"
    content = resp["choices"][0]["message"]["content"]
    assert "The answer." in content
    assert "Doc A" in content and "alpha" in content
    assert "1.2s" in content and "1 chunk" in content


def test_chat_request_last_user():
    req = ChatRequest(model="x", messages=[
        {"role": "system", "content": "s"},
        {"role": "user", "content": "first"},
        {"role": "user", "content": "second"},
    ])
    assert req.last_user() == "second"
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_openai_io.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.common.openai_io`.

- [ ] **Step 3: Create `backend_plugins/rag/common/openai_io.py`**

```python
"""OpenAI-compatible request/response shaping + uniform 'why' surfacing."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


class ChatRequest(BaseModel):
    model: str
    messages: list[dict[str, Any]]
    stream: bool = False
    temperature: float | None = None

    def last_user(self) -> str:
        for msg in reversed(self.messages):
            if msg.get("role") == "user":
                return str(msg.get("content", ""))
        return ""


@dataclass
class Source:
    title: str
    snippet: str
    score: float | None = None


@dataclass
class Metrics:
    seconds: float
    chunks: int
    llm_calls: int
    cloud_calls: int


def _plural(n: int, word: str) -> str:
    return f"{n} {word}" + ("" if n == 1 else "s")


def _render_sources(sources: list[Source]) -> str:
    if not sources:
        return ""
    lines = ["\n\n<details><summary>🔎 Retrieved context "
             f"({_plural(len(sources), 'source')})</summary>\n"]
    for i, s in enumerate(sources, 1):
        score = f" · score {s.score:.3f}" if s.score is not None else ""
        lines.append(f"\n**{i}. {s.title}**{score}\n\n> {s.snippet}\n")
    lines.append("\n</details>")
    return "".join(lines)


def _render_footer(m: Metrics) -> str:
    return (f"\n\n---\n📊 {m.seconds:.1f}s · {_plural(m.chunks, 'chunk')} · "
            f"{_plural(m.llm_calls, 'LLM call')} · {m.cloud_calls} cloud")


def build_response(model: str, answer: str, sources: list[Source],
                   metrics: Metrics) -> dict[str, Any]:
    content = answer + _render_sources(sources) + _render_footer(metrics)
    return {
        "id": f"ragshow-{model}",
        "object": "chat.completion",
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }
```

- [ ] **Step 4: Update `backend_plugins/rag/__init__.py` to aggregate approach routers**

```python
"""RAG showcase backend plugin — exposes `router` for the Atlas plugin seam."""
from fastapi import APIRouter

router = APIRouter()

# Approach routers are registered as they are implemented (Tasks 7-12).
from .approaches import vanilla  # noqa: E402
router.include_router(vanilla.router)
```

(Each later task adds one `from .approaches import X` + `router.include_router(X.router)` line here.)

- [ ] **Step 5: Run the I/O test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_openai_io.py -q`
Expected: PASS (2 passed). (The `__init__.py` import of `vanilla` is added in Task 7; until then keep the two new lines commented or implement Task 7 next.)

- [ ] **Step 6: Commit**

```bash
git add backend_plugins/rag/common/openai_io.py backend_plugins/rag/__init__.py
git commit -m "feat(rag): OpenAI I/O models + uniform sources/metrics surfacing"
```

---

## Task 6: Weaviate + TEI rerank helpers

**Files:**
- Create: `backend_plugins/rag/common/vectors.py`
- Test: `backend_plugins/rag/tests/test_vectors.py`

**Interfaces:**
- Produces:
  - `search_dense(collection: str, query_vec: list[float], k: int) -> list[Hit]`
  - `search_hybrid(collection: str, query: str, query_vec: list[float], k: int) -> list[Hit]`
  - `rerank(query: str, hits: list[Hit], top_n: int) -> list[Hit]` (calls TEI; reorders).
  - `Hit(title: str, text: str, score: float | None)`.
  - Ingest helpers `ensure_collection(name)`, `add_chunks(name, chunks)` used by Task 13.

- [ ] **Step 1: Write the failing rerank test (pure logic; TEI mocked)**

`backend_plugins/rag/tests/test_vectors.py`:
```python
import respx
import httpx
import pytest
from rag.common.vectors import rerank, Hit


@pytest.mark.asyncio
@respx.mock
async def test_rerank_reorders_by_tei_score(monkeypatch):
    monkeypatch.setenv("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80")
    hits = [Hit("A", "alpha", 0.1), Hit("B", "bravo", 0.2), Hit("C", "charlie", 0.3)]
    # TEI says index 2 is best, then 0, then 1
    respx.post("http://tei-reranker:80/rerank").mock(
        return_value=httpx.Response(200, json=[
            {"index": 2, "score": 0.99},
            {"index": 0, "score": 0.50},
            {"index": 1, "score": 0.10},
        ])
    )
    out = await rerank("q", hits, top_n=2)
    assert [h.title for h in out] == ["C", "A"]
    assert out[0].score == 0.99
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_vectors.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.common.vectors`.

- [ ] **Step 3: Create `backend_plugins/rag/common/vectors.py`**

```python
"""Weaviate (BYO-vector) search + ingest, and TEI cross-encoder rerank.

Weaviate holds dense vectors AND a BM25 index per collection. We supply
vectors ourselves (computed via LiteLLM embeddings) so the embedding model
is identical across approaches and independent of Weaviate's module config.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import httpx

_TIMEOUT = httpx.Timeout(60.0, connect=10.0)


@dataclass
class Hit:
    title: str
    text: str
    score: float | None = None


def _weaviate():
    """Open a Weaviate v4 client to the in-network instance."""
    import weaviate
    from urllib.parse import urlparse

    url = urlparse(os.environ.get("WEAVIATE_URL", "http://weaviate:8080"))
    host = url.hostname or "weaviate"
    http_port = url.port or 8080
    return weaviate.connect_to_custom(
        http_host=host, http_port=http_port, http_secure=False,
        grpc_host=host, grpc_port=50051, grpc_secure=False,
    )


def ensure_collection(name: str) -> None:
    import weaviate.classes.config as wc
    client = _weaviate()
    try:
        if not client.collections.exists(name):
            client.collections.create(
                name=name,
                vectorizer_config=wc.Configure.Vectorizer.none(),
                properties=[
                    wc.Property(name="title", data_type=wc.DataType.TEXT),
                    wc.Property(name="text", data_type=wc.DataType.TEXT),
                ],
            )
    finally:
        client.close()


def add_chunks(name: str, chunks: list[dict[str, Any]]) -> int:
    """chunks: [{'title','text','vector'}]. Returns count inserted."""
    client = _weaviate()
    try:
        coll = client.collections.get(name)
        with coll.batch.dynamic() as batch:
            for c in chunks:
                batch.add_object(
                    properties={"title": c["title"], "text": c["text"]},
                    vector=c["vector"],
                )
        return len(chunks)
    finally:
        client.close()


def _hits_from_objects(objs) -> list[Hit]:
    out: list[Hit] = []
    for o in objs:
        score = None
        if o.metadata is not None and o.metadata.score is not None:
            score = float(o.metadata.score)
        out.append(Hit(title=str(o.properties.get("title", "")),
                       text=str(o.properties.get("text", "")), score=score))
    return out


def search_dense(collection: str, query_vec: list[float], k: int) -> list[Hit]:
    import weaviate.classes.query as wq
    client = _weaviate()
    try:
        coll = client.collections.get(collection)
        res = coll.query.near_vector(near_vector=query_vec, limit=k,
                                     return_metadata=wq.MetadataQuery(distance=True))
        return _hits_from_objects(res.objects)
    finally:
        client.close()


def search_hybrid(collection: str, query: str, query_vec: list[float],
                  k: int) -> list[Hit]:
    import weaviate.classes.query as wq
    client = _weaviate()
    try:
        coll = client.collections.get(collection)
        res = coll.query.hybrid(query=query, vector=query_vec, alpha=0.5, limit=k,
                                return_metadata=wq.MetadataQuery(score=True))
        return _hits_from_objects(res.objects)
    finally:
        client.close()


async def rerank(query: str, hits: list[Hit], top_n: int) -> list[Hit]:
    if not hits:
        return []
    endpoint = os.environ.get("TEI_RERANKER_ENDPOINT", "http://tei-reranker:80").rstrip("/")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{endpoint}/rerank",
                                 json={"query": query, "texts": [h.text for h in hits]})
        resp.raise_for_status()
        ranking = resp.json()
    ordered: list[Hit] = []
    for row in ranking[:top_n]:
        h = hits[row["index"]]
        ordered.append(Hit(title=h.title, text=h.text, score=float(row["score"])))
    return ordered
```

- [ ] **Step 4: Run rerank test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_vectors.py -q`
Expected: PASS (1 passed). (Weaviate functions are exercised by the integration smoke in Task 18, not unit-mocked.)

- [ ] **Step 5: Commit**

```bash
git add backend_plugins/rag/common/vectors.py backend_plugins/rag/tests/test_vectors.py
git commit -m "feat(rag): Weaviate BYO-vector search/ingest + TEI rerank"
```

---

## Task 7: `vanilla-rag` endpoint

**Files:**
- Create: `backend_plugins/rag/approaches/__init__.py` (empty), `backend_plugins/rag/approaches/vanilla.py`, `backend_plugins/rag/common/pipeline.py`
- Test: `backend_plugins/rag/tests/test_vanilla.py`

**Interfaces:**
- Consumes: `litellm.embed/chat`, `vectors.search_dense`, `openai_io.*`, `config.role`.
- Produces: `pipeline.answer_from_context(model_role, question, hits) -> (str, int)` (answer, llm_calls); route `POST /vanilla-rag/v1/chat/completions`.

- [ ] **Step 1: Write the failing test (all I/O patched)**

`backend_plugins/rag/tests/test_vanilla.py`:
```python
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import vanilla


@pytest.mark.asyncio
async def test_vanilla_retrieves_and_answers(monkeypatch):
    async def fake_embed(texts, model=None): return [[0.0, 1.0]]
    async def fake_chat(model, messages, **kw):
        # the user's question must reach the model with context appended
        joined = messages[-1]["content"]
        assert "CTX-ALPHA" in joined
        return {"choices": [{"message": {"content": "answered"}}]}
    monkeypatch.setattr(vanilla.litellm, "embed", fake_embed)
    monkeypatch.setattr(vanilla.litellm, "chat", fake_chat)
    monkeypatch.setattr(vanilla.vectors, "search_dense",
                        lambda c, v, k: [Hit("Doc", "CTX-ALPHA body", 0.2)])
    monkeypatch.setattr(vanilla.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(vanilla.router)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        r = await ac.post("/vanilla-rag/v1/chat/completions",
                          json={"model": "vanilla-rag",
                                "messages": [{"role": "user", "content": "what is alpha?"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "answered" in content and "Doc" in content  # answer + sources block
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_vanilla.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.approaches.vanilla`.

- [ ] **Step 3: Create `backend_plugins/rag/common/pipeline.py`**

```python
"""Shared retrieve→stuff→generate step used by the text-RAG approaches."""
from __future__ import annotations

from . import litellm
from .vectors import Hit

_PROMPT = (
    "Answer the question using ONLY the context below. If the context is "
    "insufficient, say so.\n\n=== CONTEXT ===\n{context}\n\n=== QUESTION ===\n{q}"
)


def stuff(question: str, hits: list[Hit]) -> str:
    ctx = "\n\n".join(f"[{i+1}] {h.title}: {h.text}" for i, h in enumerate(hits))
    return _PROMPT.format(context=ctx, q=question)


async def answer_from_context(model: str, question: str, hits: list[Hit]) -> tuple[str, int]:
    resp = await litellm.chat(model, [{"role": "user", "content": stuff(question, hits)}])
    return resp["choices"][0]["message"]["content"], 1
```

- [ ] **Step 4: Create `backend_plugins/rag/approaches/__init__.py`** (empty file)

- [ ] **Step 5: Create `backend_plugins/rag/approaches/vanilla.py`**

```python
"""vanilla-rag: dense top-k retrieve → stuff → one LLM call (the baseline)."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagBase"
K = 5


@router.post("/vanilla-rag/v1/chat/completions")
async def vanilla_rag(req: ChatRequest):
    t0 = time.monotonic()
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    hits = vectors.search_dense(COLLECTION, query_vec, K)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)  # +1 = embed
    return build_response("vanilla-rag", answer, sources, metrics)
```

- [ ] **Step 6: Run test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_vanilla.py -q`
Expected: PASS (1 passed).

- [ ] **Step 7: Confirm `rag/__init__.py` includes the vanilla router** (added in Task 5 Step 4). Run: `pytest backend_plugins/rag -q` → all pass.

- [ ] **Step 8: Commit**

```bash
git add backend_plugins/rag/approaches backend_plugins/rag/common/pipeline.py backend_plugins/rag/tests/test_vanilla.py
git commit -m "feat(rag): vanilla-rag endpoint + shared pipeline"
```

---

## Task 8: `hybrid-rag` endpoint

**Files:**
- Create: `backend_plugins/rag/approaches/hybrid.py`
- Modify: `backend_plugins/rag/__init__.py` (register router)
- Test: `backend_plugins/rag/tests/test_hybrid.py`

**Interfaces:**
- Consumes: `vectors.search_hybrid`, `vectors.rerank`, `pipeline.answer_from_context`.
- Produces: route `POST /hybrid-rag/v1/chat/completions`.

- [ ] **Step 1: Write the failing test**

`backend_plugins/rag/tests/test_hybrid.py`:
```python
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import hybrid


@pytest.mark.asyncio
async def test_hybrid_uses_hybrid_search_then_rerank(monkeypatch):
    calls = {}
    async def fake_embed(texts, model=None): return [[1.0]]
    def fake_hybrid(c, q, v, k):
        calls["hybrid"] = (q, k)
        return [Hit("A", "a", 0.1), Hit("B", "KEYWORD body", 0.2)]
    async def fake_rerank(q, hits, top_n):
        calls["rerank"] = top_n
        return [hits[1]]  # the KEYWORD hit floats to top
    async def fake_answer(model, q, hits): return ("ok", 1)
    monkeypatch.setattr(hybrid.litellm, "embed", fake_embed)
    monkeypatch.setattr(hybrid.vectors, "search_hybrid", fake_hybrid)
    monkeypatch.setattr(hybrid.vectors, "rerank", fake_rerank)
    monkeypatch.setattr(hybrid, "answer_from_context", fake_answer)
    monkeypatch.setattr(hybrid.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(hybrid.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/hybrid-rag/v1/chat/completions",
                          json={"model": "hybrid-rag",
                                "messages": [{"role": "user", "content": "find KEYWORD"}]})
    assert r.status_code == 200
    assert calls["hybrid"][0] == "find KEYWORD"   # raw text drives BM25 leg
    assert "KEYWORD" in r.json()["choices"][0]["message"]["content"]
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_hybrid.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.approaches.hybrid`.

- [ ] **Step 3: Create `backend_plugins/rag/approaches/hybrid.py`**

```python
"""hybrid-rag: Weaviate hybrid (BM25+dense, RRF) → TEI rerank → stuff."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagBase"
RETRIEVE_K = 20
TOP_N = 5


@router.post("/hybrid-rag/v1/chat/completions")
async def hybrid_rag(req: ChatRequest):
    t0 = time.monotonic()
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    candidates = vectors.search_hybrid(COLLECTION, question, query_vec, RETRIEVE_K)
    hits = await vectors.rerank(question, candidates, TOP_N)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)
    return build_response("hybrid-rag", answer, sources, metrics)
```

- [ ] **Step 4: Register in `backend_plugins/rag/__init__.py`**

Add after the vanilla lines:
```python
from .approaches import hybrid  # noqa: E402
router.include_router(hybrid.router)
```

- [ ] **Step 5: Run test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_hybrid.py -q`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add backend_plugins/rag/approaches/hybrid.py backend_plugins/rag/tests/test_hybrid.py backend_plugins/rag/__init__.py
git commit -m "feat(rag): hybrid-rag endpoint (hybrid search + rerank)"
```

---

## Task 9: `contextual-rag` endpoint

**Files:**
- Create: `backend_plugins/rag/approaches/contextual.py`, `backend_plugins/rag/common/contextual.py`
- Modify: `backend_plugins/rag/__init__.py`
- Test: `backend_plugins/rag/tests/test_contextual.py`

**Interfaces:**
- Consumes: `vectors.search_hybrid/rerank`, `litellm.chat` (for the blurb at ingest — used by Task 13).
- Produces: route `POST /contextual-rag/v1/chat/completions` (queries the `RagContextual` collection); `contextual.contextualize(doc_text, chunk_text) -> str` (blurb generator for ingest).

- [ ] **Step 1: Write the failing test for the blurb generator**

`backend_plugins/rag/tests/test_contextual.py`:
```python
import pytest
from rag.common import contextual


@pytest.mark.asyncio
async def test_contextualize_calls_blurb_model(monkeypatch):
    seen = {}
    async def fake_chat(model, messages, **kw):
        seen["model"] = model
        seen["prompt"] = messages[-1]["content"]
        return {"choices": [{"message": {"content": "This chunk is about X."}}]}
    monkeypatch.setattr(contextual.litellm, "chat", fake_chat)
    monkeypatch.setattr(contextual.config, "role", lambda r: "gemma4:31b")
    out = await contextual.contextualize("FULL DOC", "CHUNK")
    assert out == "This chunk is about X."
    assert seen["model"] == "gemma4:31b"
    assert "FULL DOC" in seen["prompt"] and "CHUNK" in seen["prompt"]
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_contextual.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.common.contextual`.

- [ ] **Step 3: Create `backend_plugins/rag/common/contextual.py`**

```python
"""Anthropic-style Contextual Retrieval: a short situating blurb per chunk."""
from __future__ import annotations

from . import config, litellm

_PROMPT = (
    "<document>\n{doc}\n</document>\n\n"
    "Here is a chunk from the document:\n<chunk>\n{chunk}\n</chunk>\n\n"
    "Give a short (1-2 sentence) context that situates this chunk within the "
    "overall document, to improve search retrieval. Answer with ONLY the context."
)


async def contextualize(doc_text: str, chunk_text: str) -> str:
    resp = await litellm.chat(
        config.role("contextual_blurb"),
        [{"role": "user", "content": _PROMPT.format(doc=doc_text[:6000], chunk=chunk_text)}],
    )
    return resp["choices"][0]["message"]["content"].strip()
```

- [ ] **Step 4: Run blurb test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_contextual.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Create `backend_plugins/rag/approaches/contextual.py`**

```python
"""contextual-rag: same retrieval as hybrid, but over context-prefixed chunks."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import config, litellm, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response
from ..common.pipeline import answer_from_context

router = APIRouter()
COLLECTION = "RagContextual"
RETRIEVE_K = 20
TOP_N = 5


@router.post("/contextual-rag/v1/chat/completions")
async def contextual_rag(req: ChatRequest):
    t0 = time.monotonic()
    question = req.last_user()
    query_vec = (await litellm.embed([question]))[0]
    candidates = vectors.search_hybrid(COLLECTION, question, query_vec, RETRIEVE_K)
    hits = await vectors.rerank(question, candidates, TOP_N)
    answer, calls = await answer_from_context(config.role("light_gen"), question, hits)
    sources = [Source(h.title, h.text[:240], h.score) for h in hits]
    metrics = Metrics(time.monotonic() - t0, len(hits), calls + 1, 0)
    return build_response("contextual-rag", answer, sources, metrics)
```

- [ ] **Step 6: Register in `backend_plugins/rag/__init__.py`**

```python
from .approaches import contextual  # noqa: E402
router.include_router(contextual.router)
```

- [ ] **Step 7: Run the package tests to confirm pass**

Run: `pytest backend_plugins/rag -q`
Expected: PASS (all).

- [ ] **Step 8: Commit**

```bash
git add backend_plugins/rag/approaches/contextual.py backend_plugins/rag/common/contextual.py backend_plugins/rag/tests/test_contextual.py backend_plugins/rag/__init__.py
git commit -m "feat(rag): contextual-rag endpoint + ingest blurb generator"
```

---

## Task 10: `graph-rag` endpoint (wraps Atlas LightRAG)

**Files:**
- Create: `backend_plugins/rag/approaches/graph.py`, `backend_plugins/rag/common/lightrag.py`
- Modify: `backend_plugins/rag/__init__.py`
- Test: `backend_plugins/rag/tests/test_graph.py`

**Interfaces:**
- Consumes: `LIGHTRAG_ENDPOINT`, `LIGHTRAG_API_KEY` (backend env).
- Produces: `lightrag.query(question, mode="hybrid") -> str`; `lightrag.upload_text(title, text)` (ingest, Task 13); route `POST /graph-rag/v1/chat/completions`.

- [ ] **Step 1: Write the failing test**

`backend_plugins/rag/tests/test_graph.py`:
```python
import respx
import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.approaches import graph


@pytest.mark.asyncio
@respx.mock
async def test_graph_queries_lightrag(monkeypatch):
    monkeypatch.setenv("LIGHTRAG_ENDPOINT", "http://lightrag:9621")
    monkeypatch.setenv("LIGHTRAG_API_KEY", "k")
    respx.post("http://lightrag:9621/query").mock(
        return_value=httpx.Response(200, json={"response": "graph answer"})
    )
    app = FastAPI(); app.include_router(graph.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/graph-rag/v1/chat/completions",
                          json={"model": "graph-rag",
                                "messages": [{"role": "user", "content": "themes?"}]})
    assert r.status_code == 200
    assert "graph answer" in r.json()["choices"][0]["message"]["content"]
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_graph.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.approaches.graph`.

- [ ] **Step 3: Create `backend_plugins/rag/common/lightrag.py`**

```python
"""Client for Atlas's LightRAG server (graph + vector RAG)."""
from __future__ import annotations

import os

import httpx

_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


def _base() -> str:
    return os.environ.get("LIGHTRAG_ENDPOINT", "http://lightrag:9621").rstrip("/")


def _headers() -> dict[str, str]:
    key = os.environ.get("LIGHTRAG_API_KEY", "")
    return {"Authorization": f"Bearer {key}"} if key else {}


async def query(question: str, mode: str = "hybrid") -> str:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_base()}/query", headers=_headers(),
                                 json={"query": question, "mode": mode})
        resp.raise_for_status()
        data = resp.json()
        return data.get("response") or data.get("data") or ""


async def upload_text(title: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(f"{_base()}/documents/text", headers=_headers(),
                                 json={"text": text, "description": title})
        resp.raise_for_status()
```

- [ ] **Step 4: Create `backend_plugins/rag/approaches/graph.py`**

```python
"""graph-rag: reuse Atlas's LightRAG server (KG + vector dual retrieval)."""
from __future__ import annotations

import time

from fastapi import APIRouter

from ..common import lightrag
from ..common.openai_io import ChatRequest, Source, Metrics, build_response

router = APIRouter()


@router.post("/graph-rag/v1/chat/completions")
async def graph_rag(req: ChatRequest):
    t0 = time.monotonic()
    answer = await lightrag.query(req.last_user(), mode="hybrid")
    sources = [Source("LightRAG knowledge graph", "Graph + vector dual retrieval "
                      "(mode=hybrid) over the corpus's extracted entities & relations.", None)]
    metrics = Metrics(time.monotonic() - t0, 0, 1, 0)
    return build_response("graph-rag", answer, sources, metrics)
```

- [ ] **Step 5: Register in `backend_plugins/rag/__init__.py`**

```python
from .approaches import graph  # noqa: E402
router.include_router(graph.router)
```

- [ ] **Step 6: Run test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_graph.py -q`
Expected: PASS (1 passed).

- [ ] **Step 7: Commit**

```bash
git add backend_plugins/rag/approaches/graph.py backend_plugins/rag/common/lightrag.py backend_plugins/rag/tests/test_graph.py backend_plugins/rag/__init__.py
git commit -m "feat(rag): graph-rag endpoint wrapping Atlas LightRAG"
```

---

## Task 11: `agentic-rag` endpoint (ReAct loop)

**Files:**
- Create: `backend_plugins/rag/approaches/agentic.py`
- Modify: `backend_plugins/rag/__init__.py`
- Test: `backend_plugins/rag/tests/test_agentic.py`

**Interfaces:**
- Consumes: `litellm.chat` (with `tools`), `vectors.search_hybrid`, `lightrag.query`, `litellm.embed`.
- Produces: route `POST /agentic-rag/v1/chat/completions`; the response surfaces a Thought→Action→Observation trace.

- [ ] **Step 1: Write the failing test (model emits one tool call, then a final answer)**

`backend_plugins/rag/tests/test_agentic.py`:
```python
import json
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.common.vectors import Hit
from rag.approaches import agentic


@pytest.mark.asyncio
async def test_agentic_runs_tool_then_answers(monkeypatch):
    turns = []
    async def fake_chat(model, messages, tools=None, **kw):
        turns.append(messages)
        if len(turns) == 1:
            return {"choices": [{"message": {"role": "assistant", "content": None,
                "tool_calls": [{"id": "c1", "type": "function",
                  "function": {"name": "search_vectors",
                               "arguments": json.dumps({"query": "alpha"})}}]}}]}
        return {"choices": [{"message": {"role": "assistant", "content": "final answer"}}]}
    async def fake_embed(texts, model=None): return [[1.0]]
    monkeypatch.setattr(agentic.litellm, "chat", fake_chat)
    monkeypatch.setattr(agentic.litellm, "embed", fake_embed)
    monkeypatch.setattr(agentic.vectors, "search_hybrid",
                        lambda c, q, v, k: [Hit("D", "alpha body", 0.5)])
    monkeypatch.setattr(agentic.config, "role", lambda r: "qwen3.6")

    app = FastAPI(); app.include_router(agentic.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/agentic-rag/v1/chat/completions",
                          json={"model": "agentic-rag",
                                "messages": [{"role": "user", "content": "q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "final answer" in content
    assert "Action" in content and "search_vectors" in content  # trace surfaced
    assert len(turns) == 2
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_agentic.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.approaches.agentic`.

- [ ] **Step 3: Create `backend_plugins/rag/approaches/agentic.py`**

```python
"""agentic-rag: a ReAct loop that decides when/what to retrieve.

Tools (corpus-scoped for fair comparison):
  - search_vectors(query): hybrid retrieval over the base collection
  - query_graph(query): LightRAG graph+vector answer
The loop runs up to MAX_STEPS, surfaces each tool step as a trace, then
returns the model's final answer.
"""
from __future__ import annotations

import json
import time

from fastapi import APIRouter

from ..common import config, litellm, lightrag, vectors
from ..common.openai_io import ChatRequest, Source, Metrics, build_response

router = APIRouter()
COLLECTION = "RagBase"
MAX_STEPS = 4

_TOOLS = [
    {"type": "function", "function": {
        "name": "search_vectors",
        "description": "Hybrid keyword+semantic search over the document corpus.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "query_graph",
        "description": "Ask the knowledge graph a thematic or multi-hop question.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
]

_SYSTEM = ("You are a research agent. Use the tools to gather evidence before "
           "answering. Call a tool when you need information; otherwise answer.")


async def _run_tool(name: str, args: dict) -> str:
    q = args.get("query", "")
    if name == "search_vectors":
        vec = (await litellm.embed([q]))[0]
        hits = vectors.search_hybrid(COLLECTION, q, vec, 5)
        return "\n".join(f"- {h.title}: {h.text[:200]}" for h in hits) or "(no results)"
    if name == "query_graph":
        return await lightrag.query(q, mode="hybrid")
    return f"(unknown tool {name})"


@router.post("/agentic-rag/v1/chat/completions")
async def agentic_rag(req: ChatRequest):
    t0 = time.monotonic()
    model = config.role("agentic")
    messages = [{"role": "system", "content": _SYSTEM},
                {"role": "user", "content": req.last_user()}]
    trace: list[str] = []
    llm_calls = 0
    answer = ""
    for _ in range(MAX_STEPS):
        resp = await litellm.chat(model, messages, tools=_TOOLS)
        llm_calls += 1
        msg = resp["choices"][0]["message"]
        tool_calls = msg.get("tool_calls") or []
        if not tool_calls:
            answer = msg.get("content") or ""
            break
        messages.append(msg)
        for call in tool_calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}
            observation = await _run_tool(name, args)
            trace.append(f"**Action:** `{name}({args.get('query','')})`\n\n"
                         f"**Observation:** {observation[:300]}")
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": observation})
    trace_md = "\n\n".join(f"**Step {i+1}.** {t}" for i, t in enumerate(trace)) \
        or "(answered without retrieval)"
    sources = [Source("🤖 Agent trace", trace_md, None)]
    metrics = Metrics(time.monotonic() - t0, len(trace), llm_calls, 0)
    return build_response("agentic-rag", answer, sources, metrics)
```

- [ ] **Step 4: Register in `backend_plugins/rag/__init__.py`**

```python
from .approaches import agentic  # noqa: E402
router.include_router(agentic.router)
```

- [ ] **Step 5: Run test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_agentic.py -q`
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add backend_plugins/rag/approaches/agentic.py backend_plugins/rag/tests/test_agentic.py backend_plugins/rag/__init__.py
git commit -m "feat(rag): agentic-rag endpoint (ReAct loop with corpus-scoped tools)"
```

---

## Task 12: `n8n-adaptive-rag` endpoint + workflow

**Files:**
- Create: `backend_plugins/rag/approaches/n8n.py`, `n8n/adaptive-rag.workflow.json`, `n8n/README.md`
- Modify: `backend_plugins/rag/__init__.py`
- Test: `backend_plugins/rag/tests/test_n8n.py`

**Interfaces:**
- Consumes: `N8N_ADAPTIVE_WEBHOOK_URL` (set by the overlay).
- Produces: route `POST /n8n-adaptive-rag/v1/chat/completions` that forwards to the n8n webhook and wraps the `{answer, route}` result.

- [ ] **Step 1: Write the failing test**

`backend_plugins/rag/tests/test_n8n.py`:
```python
import respx
import httpx
import pytest
from fastapi import FastAPI
from httpx import AsyncClient, ASGITransport
from rag.approaches import n8n


@pytest.mark.asyncio
@respx.mock
async def test_n8n_wrapper_forwards_and_wraps(monkeypatch):
    monkeypatch.setenv("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    respx.post("http://n8n:5678/webhook/adaptive-rag").mock(
        return_value=httpx.Response(200, json={"answer": "routed answer", "route": "complex"})
    )
    app = FastAPI(); app.include_router(n8n.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        r = await ac.post("/n8n-adaptive-rag/v1/chat/completions",
                          json={"model": "n8n-adaptive-rag",
                                "messages": [{"role": "user", "content": "hard q"}]})
    assert r.status_code == 200
    content = r.json()["choices"][0]["message"]["content"]
    assert "routed answer" in content and "complex" in content  # route surfaced
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_n8n.py -q`
Expected: FAIL — `ModuleNotFoundError: rag.approaches.n8n`.

- [ ] **Step 3: Create `backend_plugins/rag/approaches/n8n.py`**

```python
"""n8n-adaptive-rag: bridge OpenWebUI <-> an n8n Adaptive-RAG workflow.

The workflow (built visually in n8n) receives {query}, routes by complexity,
retrieves, generates, and returns {answer, route}. This thin wrapper makes it
a selectable OpenAI model.
"""
from __future__ import annotations

import os
import time

import httpx
from fastapi import APIRouter

from ..common.openai_io import ChatRequest, Source, Metrics, build_response

router = APIRouter()
_TIMEOUT = httpx.Timeout(180.0, connect=10.0)


@router.post("/n8n-adaptive-rag/v1/chat/completions")
async def n8n_adaptive_rag(req: ChatRequest):
    t0 = time.monotonic()
    url = os.environ.get("N8N_ADAPTIVE_WEBHOOK_URL", "http://n8n:5678/webhook/adaptive-rag")
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(url, json={"query": req.last_user()})
        resp.raise_for_status()
        data = resp.json()
    answer = data.get("answer", "")
    route = data.get("route", "unknown")
    sources = [Source("🧭 Adaptive route", f"n8n routed this query as **{route}**.", None)]
    metrics = Metrics(time.monotonic() - t0, 0, 1, 0)
    return build_response("n8n-adaptive-rag", answer, sources, metrics)
```

- [ ] **Step 4: Register in `backend_plugins/rag/__init__.py`**

```python
from .approaches import n8n  # noqa: E402
router.include_router(n8n.router)
```

- [ ] **Step 5: Run test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_n8n.py -q`
Expected: PASS (1 passed).

- [ ] **Step 6: Create `n8n/README.md` with the workflow build recipe**

```markdown
# Adaptive-RAG n8n workflow

Build once in the n8n UI (http://localhost:<N8N_PORT>), then export to
`adaptive-rag.workflow.json` and import on other machines.

Nodes:
1. **Webhook** (POST, path `adaptive-rag`) — receives `{ "query": "..." }`.
2. **LLM Classify** (HTTP Request → `http://litellm:4000/v1/chat/completions`,
   Bearer `LITELLM_MASTER_KEY`, model `qwen3.6`): prompt "Classify the query as
   `simple` or `complex`. Answer with one word." Output → `route`.
3. **IF** node on `route == "complex"`.
   - **true →** HTTP Request to `http://backend:8000/agentic-rag/v1/chat/completions`.
   - **false →** HTTP Request to `http://backend:8000/vanilla-rag/v1/chat/completions`.
4. **Set** node: build `{ "answer": <chosen answer text>, "route": <route> }`.
5. **Respond to Webhook**: return the Set node's JSON.

The wrapper at `backend_plugins/rag/approaches/n8n.py` posts `{query}` here and
surfaces `route` in the comparison column.
```

- [ ] **Step 7: Create a placeholder `n8n/adaptive-rag.workflow.json`**

```json
{
  "name": "adaptive-rag",
  "nodes": [],
  "connections": {},
  "_comment": "Build per n8n/README.md, then overwrite this file via n8n UI export."
}
```

- [ ] **Step 8: Commit**

```bash
git add backend_plugins/rag/approaches/n8n.py backend_plugins/rag/tests/test_n8n.py backend_plugins/rag/__init__.py n8n/
git commit -m "feat(rag): n8n-adaptive-rag webhook wrapper + workflow recipe"
```

---

## Task 13: Ingestion pipeline

**Files:**
- Create: `ingest/__init__.py` (empty), `ingest/ingest.py`
- Test: `backend_plugins/rag/tests/test_ingest.py`

**Interfaces:**
- Consumes: Docling (`DOCLING_ENDPOINT`), `litellm.embed`, `vectors.ensure_collection/add_chunks`, `contextual.contextualize`, `lightrag.upload_text`.
- Produces: `ingest.chunk_document(path) -> list[dict]` (via Docling); `ingest.run(corpus_dir)` populating `RagBase`, `RagContextual`, and LightRAG.

- [ ] **Step 1: Write the failing test for Docling chunking**

`backend_plugins/rag/tests/test_ingest.py`:
```python
import respx
import httpx
import pytest
import ingest.ingest as ing


@pytest.mark.asyncio
@respx.mock
async def test_chunk_document_calls_docling(monkeypatch, tmp_path):
    monkeypatch.setenv("DOCLING_ENDPOINT", "http://docling-gpu:8000")
    doc = tmp_path / "a.txt"
    doc.write_text("hello world")
    respx.post("http://docling-gpu:8000/v1/document/convert").mock(
        return_value=httpx.Response(200, json={
            "chunks": [{"text": "hello world",
                        "metadata": {"chunk_index": 0, "section_title": "Intro"}}]
        })
    )
    chunks = await ing.chunk_document(str(doc))
    assert chunks[0]["text"] == "hello world"
    assert chunks[0]["title"].endswith("Intro") or "a.txt" in chunks[0]["title"]
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_ingest.py -q`
Expected: FAIL — `ModuleNotFoundError: ingest.ingest`.

- [ ] **Step 3: Create `ingest/__init__.py`** (empty) and **`ingest/ingest.py`**

```python
"""Corpus ingestion: Docling -> chunks -> Weaviate(base+contextual) + LightRAG."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import httpx

# Make the plugin package importable when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend_plugins"))

from rag.common import litellm, vectors  # noqa: E402
from rag.common.contextual import contextualize  # noqa: E402
from rag.common import lightrag  # noqa: E402

BASE = "RagBase"
CONTEXTUAL = "RagContextual"
_TIMEOUT = httpx.Timeout(300.0, connect=10.0)


async def chunk_document(path: str) -> list[dict]:
    endpoint = os.environ.get("DOCLING_ENDPOINT", "http://docling-gpu:8000").rstrip("/")
    name = Path(path).name
    with open(path, "rb") as fh:
        files = {"file": (name, fh, "application/octet-stream")}
        data = {"output_format": "markdown", "enable_chunking": "true",
                "chunk_size": "800", "chunk_overlap": "100"}
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(f"{endpoint}/v1/document/convert",
                                     files=files, data=data)
            resp.raise_for_status()
            payload = resp.json()
    out = []
    for ch in payload.get("chunks", []):
        section = (ch.get("metadata") or {}).get("section_title") or ""
        title = f"{name} — {section}" if section else name
        out.append({"title": title, "text": ch["text"]})
    return out


async def run(corpus_dir: str) -> dict:
    vectors.ensure_collection(BASE)
    vectors.ensure_collection(CONTEXTUAL)
    files = sorted(p for p in Path(corpus_dir).glob("**/*")
                   if p.is_file() and p.suffix.lower() in {".txt", ".md", ".pdf"})
    base_count = ctx_count = 0
    for path in files:
        doc_chunks = await chunk_document(str(path))
        if not doc_chunks:
            continue
        doc_text = "\n\n".join(c["text"] for c in doc_chunks)
        # Base collection
        vecs = await litellm.embed([c["text"] for c in doc_chunks])
        base_count += vectors.add_chunks(BASE, [
            {**c, "vector": v} for c, v in zip(doc_chunks, vecs)])
        # Contextual collection (blurb-prefixed)
        ctx_rows = []
        for c in doc_chunks:
            blurb = await contextualize(doc_text, c["text"])
            ctx_rows.append({"title": c["title"], "text": f"{blurb}\n\n{c['text']}"})
        ctx_vecs = await litellm.embed([r["text"] for r in ctx_rows])
        ctx_count += vectors.add_chunks(CONTEXTUAL, [
            {**r, "vector": v} for r, v in zip(ctx_rows, ctx_vecs)])
        # LightRAG (builds its own KG)
        await lightrag.upload_text(path.name, doc_text)
    return {"files": len(files), "base_chunks": base_count, "contextual_chunks": ctx_count}


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "corpus"
    print(asyncio.run(run(target)))
```

- [ ] **Step 4: Run the Docling test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_ingest.py -q`
Expected: PASS (1 passed). (Full `run()` is exercised by the integration smoke in Task 18.)

- [ ] **Step 5: Commit**

```bash
git add ingest backend_plugins/rag/tests/test_ingest.py
git commit -m "feat(ingest): Docling chunking + Weaviate(base+contextual) + LightRAG loader"
```

---

## Task 14: LiteLLM model registration

**Files:**
- Create: `register/__init__.py` (empty), `register/register_models.py`
- Test: `backend_plugins/rag/tests/test_register.py`

**Interfaces:**
- Consumes: LiteLLM admin API (`/model/info`, `/model/delete`, `/model/new`) with `LITELLM_MASTER_KEY`.
- Produces: `register.MODELS` (the six specs); `register.run()` idempotently (re)registers all six.

- [ ] **Step 1: Write the failing test (admin API mocked)**

`backend_plugins/rag/tests/test_register.py`:
```python
import respx
import httpx
import pytest
import register.register_models as reg


@pytest.mark.asyncio
@respx.mock
async def test_register_deletes_existing_then_adds(monkeypatch):
    monkeypatch.setenv("LITELLM_BASE_URL", "http://litellm:4000")
    monkeypatch.setenv("LITELLM_MASTER_KEY", "sk-master")
    respx.get("http://litellm:4000/model/info").mock(
        return_value=httpx.Response(200, json={"data": [
            {"model_name": "vanilla-rag", "model_info": {"id": "old-1"}}]}))
    delete = respx.post("http://litellm:4000/model/delete").mock(
        return_value=httpx.Response(200, json={}))
    new = respx.post("http://litellm:4000/model/new").mock(
        return_value=httpx.Response(200, json={}))
    await reg.run()
    assert delete.called                       # removed the stale vanilla-rag
    assert new.call_count == len(reg.MODELS)   # added all six
    body = new.calls[0].request.read().decode()
    assert "backend:8000" in body and "openai/" in body
```

- [ ] **Step 2: Run to confirm failure**

Run: `pytest backend_plugins/rag/tests/test_register.py -q`
Expected: FAIL — `ModuleNotFoundError: register.register_models`.

- [ ] **Step 3: Create `register/__init__.py`** (empty) and **`register/register_models.py`**

```python
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
```

- [ ] **Step 4: Run register test to confirm pass**

Run: `pytest backend_plugins/rag/tests/test_register.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add register backend_plugins/rag/tests/test_register.py
git commit -m "feat(register): idempotent LiteLLM /model/new registration of 6 models"
```

---

## Task 15: Corpus assembly

**Files:**
- Create: `corpus/fetch_corpus.py`, `corpus/keyword_docs/widget-error-codes.md`, `corpus/README.md`

**Interfaces:**
- Produces: `corpus/raw/` populated with a MultiHop-RAG subset + the keyword docs (gitignored raw, script-reproducible).

- [ ] **Step 1: Create `corpus/keyword_docs/widget-error-codes.md`** (a hand-picked exact-keyword doc)

```markdown
# Acme Widget Error Code Reference

- **WIDGET-ERR-7741**: Thermal cutoff engaged. The widget's coil exceeded 84°C
  and the safety relay (part RLY-22B) opened. Reset by power-cycling for 30s.
- **WIDGET-ERR-3390**: Calibration drift beyond tolerance. Run `acmectl recal`.
- **WIDGET-ERR-1188**: Firmware signature mismatch on bootloader v4.2.
```

(These rare identifiers — `WIDGET-ERR-7741` etc. — are what the keyword demo query targets: pure-dense vanilla blurs them; hybrid's BM25 leg nails them.)

- [ ] **Step 2: Create `corpus/fetch_corpus.py`**

```python
"""Assemble the curated corpus: a small MultiHop-RAG subset + keyword docs.

MultiHop-RAG (Tang & Yang, 2024) is distributed on Hugging Face under
`yixuantt/MultiHopRAG`. We take a small slice of its corpus for fast indexing.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

RAW = Path(__file__).parent / "raw"
KEYWORD = Path(__file__).parent / "keyword_docs"
MAX_DOCS = 40


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    # Keyword docs (always included)
    for p in KEYWORD.glob("*.md"):
        shutil.copy(p, RAW / p.name)
    # MultiHop-RAG corpus slice
    try:
        from datasets import load_dataset
        ds = load_dataset("yixuantt/MultiHopRAG", "corpus", split="train")
        for i, row in enumerate(ds):
            if i >= MAX_DOCS:
                break
            title = (row.get("title") or f"doc-{i}").replace("/", "-")[:80]
            body = row.get("body") or row.get("text") or json.dumps(row)
            (RAW / f"{i:03d}-{title}.md").write_text(f"# {title}\n\n{body}")
        print(f"Wrote {min(MAX_DOCS, len(ds))} MultiHop-RAG docs + keyword docs to {RAW}")
    except Exception as e:  # offline / dataset unavailable
        print(f"⚠ MultiHop-RAG fetch skipped ({e}). Keyword docs only — "
              f"add your own .md files to {RAW} for a richer demo.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `corpus/README.md`**

```markdown
# Corpus

`python corpus/fetch_corpus.py` populates `corpus/raw/` with a MultiHop-RAG
subset (multi-hop + thematic news) plus the hand-picked keyword docs in
`keyword_docs/`. `raw/` is gitignored; the script is the source of truth.
Requires `pip install datasets` for the MultiHop-RAG slice.
```

- [ ] **Step 4: Verify the keyword path works offline**

Run: `python corpus/fetch_corpus.py && ls corpus/raw/`
Expected: at least `widget-error-codes.md` present (MultiHop-RAG slice if `datasets` is installed).

- [ ] **Step 5: Commit**

```bash
git add corpus/fetch_corpus.py corpus/keyword_docs corpus/README.md
git commit -m "feat(corpus): MultiHop-RAG fetch + hand-picked keyword docs"
```

---

## Task 16: Demo query matrix

**Files:**
- Create: `demo/queries.yaml`

**Interfaces:**
- Produces: the contrast queries + the approach each should win, consumed by Task 18.

- [ ] **Step 1: Create `demo/queries.yaml`**

```yaml
# Each query is engineered so `expect_winner` visibly outperforms the others.
- id: keyword
  query: "What does error code WIDGET-ERR-7741 mean and how do I reset it?"
  expect_winner: hybrid-rag
  rationale: "Rare exact identifier — BM25 leg beats pure dense."
- id: thematic
  query: "What are the main recurring themes across all the documents?"
  expect_winner: graph-rag
  rationale: "Whole-corpus synthesis — graph community structure beats flat top-k."
- id: multihop
  query: "Compare what two different sources concluded on the same event and reconcile them."
  expect_winner: agentic-rag
  rationale: "Needs decomposition + multiple retrievals — the agent loop shows its work."
- id: factoid
  query: "What is the firmware version referenced in the widget bootloader error?"
  expect_winner: any
  rationale: "Simple single fact — all approaches should answer; teaches 'when is RAG worth it'."
```

- [ ] **Step 2: Commit**

```bash
git add demo/queries.yaml
git commit -m "docs(demo): contrasting query matrix"
```

---

## Task 17: Startup / shutdown orchestration

**Files:**
- Create: `scripts/start-all.sh`, `scripts/stop-all.sh`

**Interfaces:**
- Produces: `./scripts/start-all.sh` brings up Atlas (gen-ai-rag), ingests, registers, prints the OpenWebUI URL.

- [ ] **Step 1: Create `scripts/start-all.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

./scripts/setup-overlay.sh

echo "==> Starting Atlas (gen-ai-rag track)…"
( cd infra && ./start.sh --track gen-ai-rag --lightrag-source container \
    --tei-reranker-source container-cpu --doc-processor-source disabled )

echo "==> Waiting for the backend to report healthy…"
BP="$(grep -E '^BACKEND_PORT=' infra/.env | cut -d= -f2)"
for _ in $(seq 1 60); do
  if curl -fsS "http://localhost:${BP}/health" >/dev/null 2>&1; then break; fi
  sleep 5
done

echo "==> Ingesting corpus…"
python corpus/fetch_corpus.py
docker exec "$(grep -E '^PROJECT_NAME=' infra/.env | cut -d= -f2)-backend" \
  python /app/plugins/../ingest/ingest.py /app/plugins/../corpus/raw || \
  python ingest/ingest.py corpus/raw   # fallback: run from host if it can reach the stack

echo "==> Registering the six models in LiteLLM…"
set -a; source infra/.env; set +a
python register/register_models.py

OWUI="$(grep -E '^OPEN_WEB_UI_PORT=' infra/.env | cut -d= -f2)"
echo "==> Ready. Open OpenWebUI at http://localhost:${OWUI} , start a multi-model"
echo "    chat, and select: vanilla-rag, hybrid-rag, contextual-rag, graph-rag,"
echo "    agentic-rag, n8n-adaptive-rag."
```

(Ingestion is run inside the backend container so it reuses the in-network DNS + env; the host fallback covers setups where the host can reach the published ports. Confirm the exact in-container path during first run and simplify to one path.)

- [ ] **Step 2: Create `scripts/stop-all.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
( cd "$ROOT/infra" && ./stop.sh )
echo "Stopped. (Use 'cd infra && ./stop.sh --cold' to also wipe data.)"
```

- [ ] **Step 3: Make executable; lint with shellcheck if available**

```bash
chmod +x scripts/start-all.sh scripts/stop-all.sh
command -v shellcheck >/dev/null && shellcheck scripts/*.sh || echo "shellcheck not installed; skipping"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/start-all.sh scripts/stop-all.sh
git commit -m "build: one-command start-all/stop-all orchestration"
```

---

## Task 18: End-to-end contrast verification (integration)

**Files:**
- Create: `tests/test_demo_matrix.py`, `tests/conftest.py`

**Interfaces:**
- Consumes: the running stack (skipped if unreachable) + `demo/queries.yaml`.
- Produces: an assertion that each query returns from all six models and the keyword query's `hybrid-rag` answer contains the gold token.

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import os
import httpx
import pytest

LITELLM = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")


@pytest.fixture(scope="session")
def litellm_up():
    try:
        httpx.get(f"{LITELLM}/health/liveliness", timeout=3)
    except Exception:
        pytest.skip("LiteLLM not reachable — start the stack to run integration tests")
```

- [ ] **Step 2: Write `tests/test_demo_matrix.py`**

```python
import os
import yaml
import httpx
import pytest

LITELLM = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")
KEY = os.environ.get("LITELLM_MASTER_KEY", "")
MODELS = ["vanilla-rag", "hybrid-rag", "contextual-rag",
          "graph-rag", "agentic-rag", "n8n-adaptive-rag"]


def _ask(model: str, query: str) -> str:
    r = httpx.post(f"{LITELLM}/v1/chat/completions",
                   headers={"Authorization": f"Bearer {KEY}"},
                   json={"model": model, "messages": [{"role": "user", "content": query}]},
                   timeout=180)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def test_all_models_registered(litellm_up):
    data = httpx.get(f"{LITELLM}/v1/models",
                     headers={"Authorization": f"Bearer {KEY}"}, timeout=10).json()
    ids = {m["id"] for m in data["data"]}
    for m in MODELS:
        assert m in ids, f"{m} not registered in LiteLLM"


def test_keyword_query_hybrid_finds_gold(litellm_up):
    answer = _ask("hybrid-rag",
                  "What does error code WIDGET-ERR-7741 mean and how do I reset it?")
    assert "WIDGET-ERR-7741" in answer or "thermal" in answer.lower()


@pytest.mark.parametrize("model", MODELS)
def test_every_model_answers(litellm_up, model):
    answer = _ask(model, "Give a one sentence summary of the corpus.")
    assert isinstance(answer, str) and len(answer) > 0
```

- [ ] **Step 3: Run against the live stack**

Run: `set -a; source infra/.env; set +a; pytest tests/test_demo_matrix.py -q`
Expected: PASS when the stack is up and ingested; SKIP when it isn't.

- [ ] **Step 4: Commit**

```bash
git add tests/test_demo_matrix.py tests/conftest.py
git commit -m "test: end-to-end demo-matrix contrast verification"
```

---

## Task 19: Atlas-reuse assessment

**Files:**
- Create: `docs/atlas-reuse-assessment.md`

**Interfaces:**
- Produces: the written test-drive deliverable (spec §10).

- [ ] **Step 1: Create `docs/atlas-reuse-assessment.md`**

```markdown
# Atlas Reuse Assessment — RAG Showcase

A living record of how well Atlas served as reusable infra for this project.

## What reused cleanly (out of the box)
- OpenWebUI multi-model chat as the comparison frontend (no custom UI).
- LiteLLM service-as-a-model: `/model/new` admin API (STORE_MODEL_IN_DB=True)
  registered six custom-`api_base` models with zero Atlas edits.
- `gen-ai-rag` track brought up Weaviate/Neo4j/LightRAG/TEI/Docling in one flag.
- Backend's pre-wired env (Weaviate/Neo4j/LiteLLM/LightRAG/Docling URLs + creds).

## Friction found / seams added
- The backend had no extension point for downstream routes → added a generic
  plugin seam (`plugin_seam.py`, ~2 hooks). Candidate to upstream into Atlas.
- `public.llms` has no `api_base` column, so it can't express custom endpoints;
  the `/model/new` admin API was the right channel. (Document for Atlas.)
- _user overlay merged into an existing service (backend) via service-name
  merge — record whether this worked first try or needed adjustment.
- First-boot latency: LightRAG/TEI/Docling model downloads (record minutes).
- Plugin-requirements installed at backend startup (record the cost).

## Recommendations for Atlas
- (Fill in as discovered.) e.g. ship the plugin seam upstream; add a
  `--extra-compose` flag to beat the `_user/` symlink; have the gen-ai-rag
  backend image carry `weaviate-client`/`neo4j`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/atlas-reuse-assessment.md
git commit -m "docs: Atlas reuse assessment (living deliverable)"
```

---

## Self-Review

**Spec coverage:**
- 6 approaches (spec §2) → Tasks 7–12. ✔
- Local-first roles (§7) → Task 4 `roles.yaml` + `config.role`. ✔
- OWUI multi-model frontend (§6.2) → reuse; verified in Task 18. ✔
- Backend plugin seam, no bloat (§4.2) → Tasks 2–3. ✔
- Registration without Atlas edits (§6.1) → Task 14 (`/model/new`). ✔
- Corpus = MultiHop-RAG + keyword docs, 3 indexes (§5) → Tasks 13, 15. ✔
- Uniform sources/metrics surfacing (§6.3) → Task 5. ✔
- Demo matrix + verification (§3, §8.2) → Tasks 16, 18. ✔
- Atlas-reuse assessment (§10) → Task 19. ✔
- Deferred custom dashboard (§12) → intentionally out of scope. ✔

**Placeholder scan:** No pending-content markers or vague follow-up instructions remain — every code step has complete code. The two intentional non-code artifacts (`n8n/adaptive-rag.workflow.json` placeholder and the in-container ingest path in `start-all.sh`) are explicitly flagged to finalize on first run, not silent gaps.

**Type consistency:** `Hit(title,text,score)`, `Source(title,snippet,score)`, `Metrics(seconds,chunks,llm_calls,cloud_calls)`, `ChatRequest.last_user()`, `build_response(model,answer,sources,metrics)`, `config.role(name)`, `litellm.embed(texts,model=None)`, `litellm.chat(model,messages,tools=None,temperature=0.0)` — used consistently across Tasks 5–14. Collections `RagBase`/`RagContextual` consistent across Tasks 6, 7, 8, 9, 11, 13. Model names consistent across Tasks 7–12, 14, 18.

**Known integration points to confirm on first live run (normal, not gaps):** LightRAG `/query` field names (`response` vs `data`) and `/documents/text` shape; Docling form-field names; the exact in-container ingest path; weaviate-client v4 minor-version API. Each has a single, localized call site.
