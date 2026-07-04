import os

import httpx
import pytest

from compare.run_matrix import envval  # the repo's one .env parser (last-assignment-wins)

# Prefer explicit env overrides; else derive the host-published gateway from
# infra/.env, so "start the stack" alone un-skips the integration tests (Atlas
# publishes LiteLLM on LITELLM_PORT, not on the container-internal 4000); else
# fall back to LiteLLM's default.
LITELLM = (os.environ.get("LITELLM_BASE_URL")
           or (f"http://localhost:{envval('LITELLM_PORT')}"
               if envval("LITELLM_PORT") else "")
           or "http://localhost:4000")
KEY = os.environ.get("LITELLM_MASTER_KEY") or envval("LITELLM_MASTER_KEY") or ""


@pytest.fixture(scope="session")
def litellm_up():
    try:
        r = httpx.get(f"{LITELLM}/health/liveliness", timeout=3)
        r.raise_for_status()  # a reachable-but-unhealthy (e.g. 503) gateway must skip too
    except Exception:
        pytest.skip(f"LiteLLM not reachable/healthy at {LITELLM} — start the stack "
                    "(scripts/start-all.sh), or export LITELLM_BASE_URL and "
                    "LITELLM_MASTER_KEY for a non-default gateway")
