from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, status

from app.auth.dependencies import get_current_active_user
from app.common.dependencies import get_pagination
from app.common.responses import success_response
from app.common.schemas import PaginationParams
from app.scheduling.dependencies import (
    get_event_service,
    require_event_permission,
    require_organization_event_permission,
)
from app.scheduling.schemas import EventCreate, EventResponse, EventUpdate
from app.scheduling.service import EventService
from app.users.models import User

router = APIRouter(tags=["scheduling"])


@router.get("/organizations/{org_id}/scheduling/events")
async def list_events(
    org_id: UUID,
    start_date: datetime,
    end_date: datetime,
    pagination: PaginationParams = Depends(get_pagination),
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_event_permission("scheduling:read")),
    service: EventService = Depends(get_event_service),
) -> dict[str, Any]:
    items, meta = await service.list_events(
        organization_id=org_id,
        start_date=start_date,
        end_date=end_date,
        pagination=pagination,
    )
    return success_response(
        data=[EventResponse.model_validate(e) for e in items],
        meta={"pagination": meta.model_dump()},
    )


@router.post("/organizations/{org_id}/scheduling/events", status_code=status.HTTP_201_CREATED)
async def create_event(
    org_id: UUID,
    data: EventCreate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_organization_event_permission("scheduling:create")),
    service: EventService = Depends(get_event_service),
) -> dict[str, Any]:
    create_data = EventCreate(**{**data.model_dump(), "organization_id": org_id})
    event = await service.create(create_data, current_user)
    return success_response(
        data=EventResponse.model_validate(event),
        message="Event created successfully.",
    )


@router.get("/scheduling/events/{event_id}")
async def get_event_by_id(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_event_permission("scheduling:read")),
    service: EventService = Depends(get_event_service),
) -> dict[str, Any]:
    event = await service.get(event_id)
    return success_response(data=EventResponse.model_validate(event))


@router.patch("/scheduling/events/{event_id}")
async def update_event(
    event_id: UUID,
    data: EventUpdate,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_event_permission("scheduling:update")),
    service: EventService = Depends(get_event_service),
) -> dict[str, Any]:
    event = await service.update(event_id, data, current_user)
    return success_response(
        data=EventResponse.model_validate(event),
        message="Event updated successfully.",
    )


@router.delete("/scheduling/events/{event_id}")
async def delete_event(
    event_id: UUID,
    current_user: User = Depends(get_current_active_user),
    _: User = Depends(require_event_permission("scheduling:delete")),
    service: EventService = Depends(get_event_service),
) -> dict[str, Any]:
    await service.delete(event_id, current_user)
    return success_response(message="Event deleted successfully.")
