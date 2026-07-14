"""RAG showcase backend plugin — exposes `router` for the Atlas plugin seam."""
from fastapi import APIRouter

from .common import flavors


router = APIRouter(prefix="/rag")


@router.get("/health")
async def health() -> dict[str, object]:
    """Report plugin liveness and the approach routes mounted under this root."""
    return {
        "status": "ok",
        "plugin": "rag-showcase",
        "approaches": sorted(flavors.BASE_APPROACHES),
        "experimental_approaches": sorted(flavors.EXPERIMENTAL_APPROACHES),
    }

# Include all six approach routers onto the aggregate router the seam loads.
from .approaches import vanilla  # noqa: E402
router.include_router(vanilla.router)
from .approaches import hybrid  # noqa: E402
router.include_router(hybrid.router)
from .approaches import contextual  # noqa: E402
router.include_router(contextual.router)
from .approaches import graph  # noqa: E402
router.include_router(graph.router)
from .approaches import agentic  # noqa: E402
router.include_router(agentic.router)
from .approaches import n8n  # noqa: E402
router.include_router(n8n.router)
from .approaches import lazy  # noqa: E402
router.include_router(lazy.router)
