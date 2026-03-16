"""Health check routes."""

import os

from fastapi import APIRouter

router = APIRouter(tags=["Health"])

VERSION = "0.1.0"


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint for Docker Compose and monitoring."""
    storage_mode = os.getenv("STORAGE_MODE", "local")
    return {
        "status": "ok",
        "version": VERSION,
        "storage_mode": storage_mode,
        "aleph_connected": storage_mode == "aleph",
    }
