"""Collection-request HTTP layer — thin handlers delegating to RequestService.

Endpoints:
  POST   /requests                  create (hotel manager)
  GET    /requests                  list / operator queue (priority-sorted)
  GET    /requests/{id}             detail
  POST   /requests/{id}/decision    accept / reject (operator)
  POST   /requests/{id}/transition  on_the_way | collected | completed (operator)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.features.requests.dependencies import RequestServiceDep
from app.features.requests.schemas import (
    CollectionRequestCreate,
    CollectionRequestRead,
    RequestDecision,
    RequestTransition,
)
from app.features.requests.state_machine import RequestStatus
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

Pagination = Annotated[PaginationParams, Depends(pagination_params)]
OperatorOrAdmin = [Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN))]


@router.post(
    "",
    response_model=CollectionRequestRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a collection request (hotel)",
    dependencies=[Depends(require_role(UserRole.HOTEL_MANAGER))],
)
async def create_request(
    payload: CollectionRequestCreate,
    service: RequestServiceDep,
    current_user: CurrentUser,
    hotel_id: Annotated[
        uuid.UUID | None,
        Query(description="Required only if you manage multiple hotels."),
    ] = None,
) -> CollectionRequestRead:
    req = await service.create(payload, current_user, hotel_id=hotel_id)
    return CollectionRequestRead.model_validate(req)


@router.get(
    "",
    response_model=Page[CollectionRequestRead],
    summary="List requests (operator queue, priority-sorted)",
)
async def list_requests(
    current_user: CurrentUser,
    service: RequestServiceDep,
    params: Pagination,
    status_filter: Annotated[RequestStatus | None, Query(alias="status")] = None,
    hotel_id: Annotated[uuid.UUID | None, Query()] = None,
) -> Page[CollectionRequestRead]:
    return await service.list(
        params=params,
        user=current_user,
        status=status_filter,
        hotel_id=hotel_id,
    )


@router.get(
    "/{request_id}",
    response_model=CollectionRequestRead,
    summary="Get a request",
)
async def get_request(
    request_id: uuid.UUID,
    service: RequestServiceDep,
    current_user: CurrentUser,
) -> CollectionRequestRead:
    req = await service.get_or_404(request_id, current_user)
    return CollectionRequestRead.model_validate(req)


@router.post(
    "/{request_id}/decision",
    response_model=CollectionRequestRead,
    summary="Accept or reject a request (operator)",
    dependencies=OperatorOrAdmin,
)
async def decide_request(
    request_id: uuid.UUID,
    payload: RequestDecision,
    service: RequestServiceDep,
    current_user: CurrentUser,
) -> CollectionRequestRead:
    req = await service.decide(request_id, payload, current_user)
    return CollectionRequestRead.model_validate(req)


@router.post(
    "/{request_id}/transition",
    response_model=CollectionRequestRead,
    summary="Advance an accepted request (operator)",
    dependencies=OperatorOrAdmin,
)
async def transition_request(
    request_id: uuid.UUID,
    payload: RequestTransition,
    service: RequestServiceDep,
    current_user: CurrentUser,
) -> CollectionRequestRead:
    req = await service.transition(request_id, payload, current_user)
    return CollectionRequestRead.model_validate(req)
