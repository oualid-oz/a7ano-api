from datetime import datetime
from uuid import UUID

from app.common.schemas import PaginationMeta, PaginationParams
from app.core.logging import get_logger
from app.organizations.repository import OrganizationRepository
from app.scheduling.exceptions import EventNotFoundException
from app.scheduling.models import Event
from app.scheduling.repository import EventRepository
from app.scheduling.schemas import EventCreate, EventUpdate
from app.users.models import User

logger = get_logger(__name__)


class EventService:
    def __init__(
        self,
        event_repository: EventRepository,
        organization_repository: OrganizationRepository,
    ) -> None:
        self._event_repository = event_repository
        self._organization_repository = organization_repository

    async def create(self, data: EventCreate, current_user: User) -> Event:
        logger.info(
            "Creating event",
            extra={
                "org_id": str(data.organization_id),
                "title": data.title,
                "user_id": str(current_user.id),
            },
        )
        if data.organization_id is None:
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        logger.info(
            "Calling OrganizationRepository.get_active_by_id",
            extra={"org_id": str(data.organization_id)},
        )
        organization = await self._organization_repository.get_active_by_id(
            data.organization_id,
        )
        if organization is None:
            logger.warning(
                "Create event failed: organization not found",
                extra={"org_id": str(data.organization_id)},
            )
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        event = Event(
            organization_id=data.organization_id,
            title=data.title,
            description=data.description,
            start_time=data.start_time,
            end_time=data.end_time,
            location=data.location,
            color=data.color,
            all_day=data.all_day,
            created_by=current_user.id,
            updated_by=current_user.id,
        )
        event = await self._event_repository.create(event)
        logger.info(
            "Event created",
            extra={
                "event_id": str(event.id),
                "title": event.title,
                "org_id": str(event.organization_id),
            },
        )
        return event

    async def get(self, event_id: UUID) -> Event:
        logger.info("Fetching event", extra={"event_id": str(event_id)})
        event = await self._event_repository.get_active_by_id(event_id)
        if event is None:
            logger.warning("Event not found", extra={"event_id": str(event_id)})
            raise EventNotFoundException()
        logger.info("Event fetched", extra={"event_id": str(event.id), "title": event.title})
        return event

    async def update(self, event_id: UUID, data: EventUpdate, current_user: User) -> Event:
        logger.info(
            "Updating event", extra={"event_id": str(event_id), "user_id": str(current_user.id)}
        )
        event = await self.get(event_id)
        update_data = data.model_dump(exclude_unset=True)
        update_data["updated_by"] = current_user.id
        logger.info(
            "Updating event fields",
            extra={"event_id": str(event_id), "fields": list(update_data.keys())},
        )
        updated = await self._event_repository.update(event, update_data)
        logger.info("Event updated", extra={"event_id": str(updated.id)})
        return updated

    async def delete(self, event_id: UUID, current_user: User) -> Event:
        logger.info(
            "Deleting event", extra={"event_id": str(event_id), "user_id": str(current_user.id)}
        )
        event = await self.get(event_id)
        event.updated_by = current_user.id
        deleted = await self._event_repository.delete_soft(event)
        logger.info("Event deleted", extra={"event_id": str(event_id)})
        return deleted

    async def list_events(
        self,
        organization_id: UUID,
        start_date: datetime,
        end_date: datetime,
        pagination: PaginationParams,
    ) -> tuple[list[Event], PaginationMeta]:
        logger.info(
            "Listing events",
            extra={
                "org_id": str(organization_id),
                "start_date": str(start_date),
                "end_date": str(end_date),
                "page": pagination.page,
            },
        )
        organization = await self._organization_repository.get_active_by_id(organization_id)
        if organization is None:
            logger.warning(
                "List events failed: organization not found", extra={"org_id": str(organization_id)}
            )
            from app.organizations.exceptions import OrganizationNotFoundException

            raise OrganizationNotFoundException()

        events, meta = await self._event_repository.list_by_organization_and_range(
            organization_id=organization_id,
            start_date=start_date,
            end_date=end_date,
            pagination=pagination,
        )
        logger.info(
            "Events list response", extra={"org_id": str(organization_id), "total": meta.total}
        )
        return events, meta
