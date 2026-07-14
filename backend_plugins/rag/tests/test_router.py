"""The aggregate plugin router is what the Atlas seam mounts — pin its route set."""
from rag import router
from rag.common import flavors


def test_plugin_router_exposes_canonical_and_explicit_experimental_routes():
    # Deleting one include_router() line in rag/__init__.py previously 404'd that
    # approach in production with the whole suite green: every test mounts the
    # per-approach sub-router, and imports alone gave __init__ 100% line coverage.
    paths = {route.path for route in router.routes}
    assert paths == {
        "/rag/health",
        *(f"/rag/{name}/v1/chat/completions" for name in flavors.SUPPORTED_APPROACHES),
    }
