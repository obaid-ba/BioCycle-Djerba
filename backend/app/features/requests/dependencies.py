"""Reusable dependencies for the requests HTTP layer.

This is the single place where the request **data provider** is chosen and
injected. To go live with Firebase later, return a `FirebaseRealtimeReader` from
`get_data_provider` — nothing else changes (Adapter pattern + DI).
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.requests.data_provider import (
    RequestDataProvider,
    default_provider,
)
from app.features.requests.service import RequestService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_data_provider() -> RequestDataProvider:
    """The analysis-data source for requests.

    Returns the stub today; swap the return value for the Firebase reader when
    the integration lands. The business layer never references this choice.
    """
    return default_provider


DataProviderDep = Annotated[RequestDataProvider, Depends(get_data_provider)]


def get_request_service(
    db: DbSession, data_provider: DataProviderDep
) -> RequestService:
    """Provide a RequestService bound to the request-scoped DB session and the
    injected data provider. Handlers stay free of wiring."""
    return RequestService(db, data_provider=data_provider)


RequestServiceDep = Annotated[RequestService, Depends(get_request_service)]
