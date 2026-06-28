"""Top-level API router.

Each feature exposes its own `router`; we aggregate them here so `main.py` only
mounts a single router under the API prefix. New features are wired in with one
line — this file is the API's table of contents.
"""

from fastapi import APIRouter

from app.features.health.router import router as health_router

api_router = APIRouter()
api_router.include_router(health_router)

# Wired in later phases:
# api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
# api_router.include_router(hotels_router, prefix="/hotels", tags=["Hotels"])
