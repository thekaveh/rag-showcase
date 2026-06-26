"""RAG showcase backend plugin — exposes `router` for the Atlas plugin seam."""
from fastapi import APIRouter

router = APIRouter()

# Approach routers are registered by later tasks as they are implemented.
from .approaches import vanilla  # noqa: E402
router.include_router(vanilla.router)
from .approaches import hybrid  # noqa: E402
router.include_router(hybrid.router)
