"""Reusable dependencies for the requests HTTP layer.

This is the single place where the request **data provider** is chosen and
injected. To go live with Firebase later, return a `FirebaseRealtimeReader` from
`get_data_provider` — nothing else changes (Adapter pattern + DI).
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.features.requests.data_provider import (
    RequestDataProvider,
    default_provider,
)
from app.features.requests.service import RequestService

DbSession = Annotated[AsyncSession, Depends(get_db)]


@lru_cache
def _firebase_provider() -> RequestDataProvider:
    # Imported lazily so the Firebase deps are only loaded when enabled.
    from app.integrations.firebase.reader import FirebaseRealtimeReader

    return FirebaseRealtimeReader()


def get_data_provider() -> RequestDataProvider:
    """The analysis-data source for requests — the single swap point.

    Firebase when FIREBASE_ENABLED (reads camera detections, read-only);
    otherwise the deterministic stub. The business layer never references this
    choice (Adapter + DI).
    """
    if settings.FIREBASE_ENABLED:
        return _firebase_provider()
    return default_provider


DataProviderDep = Annotated[RequestDataProvider, Depends(get_data_provider)]


def get_request_service(
    db: DbSession, data_provider: DataProviderDep
) -> RequestService:
    """Provide a RequestService bound to the request-scoped DB session and the
    injected data provider. Handlers stay free of wiring."""
    return RequestService(db, data_provider=data_provider)


RequestServiceDep = Annotated[RequestService, Depends(get_request_service)]
