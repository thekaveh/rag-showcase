"""The aggregate plugin router is what the Atlas seam mounts — pin its route set."""
from rag import router
from rag.common import flavors


def test_plugin_router_exposes_all_six_approach_routes():
    # Deleting one include_router() line in rag/__init__.py previously 404'd that
    # approach in production with the whole suite green: every test mounts the
    # per-approach sub-router, and imports alone gave __init__ 100% line coverage.
    paths = {route.path for route in router.routes}
    assert paths == {f"/{name}/v1/chat/completions" for name in flavors.BASE_APPROACHES}
