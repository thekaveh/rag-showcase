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
