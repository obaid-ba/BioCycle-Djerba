"""Reusable dependencies for the requests HTTP layer."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.features.requests.service import RequestService

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_request_service(db: DbSession) -> RequestService:
    """Provide a RequestService bound to the request-scoped DB session.

    Centralizing construction here keeps handlers free of wiring and gives a
    single place to swap the AI scorer (e.g. the real HTTP client) later.
    """
    return RequestService(db)


RequestServiceDep = Annotated[RequestService, Depends(get_request_service)]
