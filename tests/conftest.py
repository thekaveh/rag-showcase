import os
import httpx
import pytest

LITELLM = os.environ.get("LITELLM_BASE_URL", "http://localhost:4000")


@pytest.fixture(scope="session")
def litellm_up():
    try:
        r = httpx.get(f"{LITELLM}/health/liveliness", timeout=3)
        r.raise_for_status()  # a reachable-but-unhealthy (e.g. 503) gateway must skip too
    except Exception:
        pytest.skip("LiteLLM not reachable/healthy — start the stack to run integration tests")
