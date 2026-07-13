"""Collection-request HTTP layer — thin handlers delegating to RequestService.

Endpoints:
  POST   /requests                       create (hotel manager)
  GET    /requests                       list / operator queue (priority-sorted)
  GET    /requests/{id}                  detail
  POST   /requests/{id}/decision         accept / reject (operator)
  POST   /requests/{id}/transition       on_the_way | collected | completed (operator)
  POST   /requests/{id}/photos           upload photos (hotel owner)
  GET    /requests/{id}/photos/{pid}     download a photo (JWT + access check)
  DELETE /requests/{id}/photos/{pid}     delete a photo (hotel owner)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.database import get_db
from app.features.auth.dependencies import CurrentUser, require_role
from app.features.auth.models import UserRole
from app.features.requests.dependencies import RequestServiceDep
from app.features.requests.photo_service import PhotoService
from app.features.requests.schemas import (
    CollectionRequestCreate,
    CollectionRequestRead,
    RequestDecision,
    RequestPhotoRead,
    RequestTransition,
)
from app.features.requests.state_machine import RequestStatus
from app.shared.schemas import Page, PaginationParams, pagination_params

router = APIRouter()

Pagination = Annotated[PaginationParams, Depends(pagination_params)]
OperatorOrAdmin = [Depends(require_role(UserRole.OPERATOR, UserRole.ADMIN))]


def get_photo_service(db=Depends(get_db)) -> PhotoService:
    return PhotoService(db)


PhotoServiceDep = Annotated[PhotoService, Depends(get_photo_service)]


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


# --------------------------------------------------------------------------- #
# Photos
# --------------------------------------------------------------------------- #
@router.post(
    "/{request_id}/photos",
    response_model=list[RequestPhotoRead],
    status_code=status.HTTP_201_CREATED,
    summary="Upload one or more photos to a request (hotel owner)",
    dependencies=[Depends(require_role(UserRole.HOTEL_MANAGER))],
)
async def upload_photos(
    request_id: uuid.UUID,
    service: PhotoServiceDep,
    current_user: CurrentUser,
    files: Annotated[list[UploadFile], File(description="JPEG/PNG/WebP, ≤10MB each")],
) -> list[RequestPhotoRead]:
    photos = await service.upload(request_id, files, current_user)
    return [RequestPhotoRead.model_validate(p) for p in photos]


@router.get(
    "/{request_id}/photos/{photo_id}",
    summary="Download a request photo (JWT + access check; not public)",
    response_class=FileResponse,
)
async def get_photo(
    request_id: uuid.UUID,
    photo_id: uuid.UUID,
    service: PhotoServiceDep,
    current_user: CurrentUser,
) -> FileResponse:
    path, content_type = await service.get_file(request_id, photo_id, current_user)
    # inline so browsers render it; no download prompt.
    return FileResponse(path, media_type=content_type, content_disposition_type="inline")


@router.delete(
    "/{request_id}/photos/{photo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a request photo (hotel owner)",
    dependencies=[Depends(require_role(UserRole.HOTEL_MANAGER))],
)
async def delete_photo(
    request_id: uuid.UUID,
    photo_id: uuid.UUID,
    service: PhotoServiceDep,
    current_user: CurrentUser,
) -> None:
    await service.delete(request_id, photo_id, current_user)
