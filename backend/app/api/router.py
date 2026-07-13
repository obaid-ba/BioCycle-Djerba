"""Top-level API router.

Each feature exposes its own `router`; we aggregate them here so `main.py` only
mounts a single router under the API prefix. New features are wired in with one
line — this file is the API's table of contents.
"""

from fastapi import APIRouter

from app.features.activity.router import router as activity_router
from app.features.alerts.router import router as alerts_router
from app.features.analytics.router import (
    analytics_router,
    dashboard_router,
)
from app.features.auth.router import router as auth_router
from app.features.bins.router import router as bins_router
from app.features.collections.router import router as collections_router
from app.features.health.router import router as health_router
from app.features.hotels.router import router as hotels_router
from app.features.requests.router import router as requests_router
from app.realtime.router import router as realtime_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(hotels_router, prefix="/hotels", tags=["Hotels"])
api_router.include_router(requests_router, prefix="/requests", tags=["Collection Requests"])
api_router.include_router(bins_router, prefix="/bins", tags=["Smart Bins"])
api_router.include_router(collections_router, prefix="/collections", tags=["Waste Collections"])
api_router.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(activity_router, prefix="/activity-logs", tags=["Activity Logs"])
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(analytics_router, prefix="/analytics", tags=["Analytics"])
api_router.include_router(realtime_router, tags=["Realtime"])
