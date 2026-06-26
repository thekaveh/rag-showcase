"""RAG showcase backend plugin — exposes `router` for the Atlas plugin seam."""
from fastapi import APIRouter

router = APIRouter()

# Approach routers are registered by later tasks as they are implemented.
