"""Unit tests for EventService."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.common.schemas import PaginationMeta, PaginationParams
from app.organizations.exceptions import OrganizationNotFoundException
from app.scheduling.exceptions import EventNotFoundException
from app.scheduling.models import Event
from app.scheduling.schemas import EventCreate, EventUpdate
from app.scheduling.service import EventService


def _make_user(user_id: UUID | None = None) -> MagicMock:
    user = MagicMock()
    user.id = user_id or uuid4()
    user.email = "user@example.com"
    user.full_name = "Test User"
    user.deleted_at = None
    return user


def _make_organization(org_id: UUID | None = None) -> MagicMock:
    org = MagicMock()
    org.id = org_id or uuid4()
    org.name = "Test Org"
    org.deleted_at = None
    return org


def _make_event(
    event_id: UUID | None = None,
    org_id: UUID | None = None,
    title: str = "Test Event",
) -> MagicMock:
    event = MagicMock(spec=Event)
    event.id = event_id or uuid4()
    event.organization_id = org_id or uuid4()
    event.title = title
    event.description = None
    event.start_time = datetime.now(UTC)
    event.end_time = datetime.now(UTC) + timedelta(hours=1)
    event.location = None
    event.color = "indigo"
    event.all_day = False
    event.created_by = None
    event.updated_by = None
    event.deleted_at = None
    return event


@pytest.mark.anyio
class TestEventService:
    def _make_service(
        self,
        event_repo: Any | None = None,
        org_repo: Any | None = None,
    ) -> EventService:
        return EventService(
            event_repository=event_repo or AsyncMock(),
            organization_repository=org_repo or AsyncMock(),
        )

    async def test_create_event_success(self) -> None:
        org_id = uuid4()
        org = _make_organization(org_id=org_id)
        user = _make_user()
        created_event = _make_event(org_id=org_id)

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org
        event_repo = AsyncMock()
        event_repo.create.return_value = created_event

        service = self._make_service(event_repo=event_repo, org_repo=org_repo)
        start = datetime.now(UTC)
        end = start + timedelta(hours=1)
        data = EventCreate(
            organization_id=org_id,
            title="New Event",
            start_time=start,
            end_time=end,
        )
        result = await service.create(data, user)

        assert result is created_event
        event_repo.create.assert_awaited_once()

    async def test_create_event_org_not_found_raises(self) -> None:
        org_id = uuid4()
        user = _make_user()

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = None

        service = self._make_service(org_repo=org_repo)
        start = datetime.now(UTC)
        data = EventCreate(
            organization_id=org_id,
            title="New Event",
            start_time=start,
            end_time=start + timedelta(hours=1),
        )

        with pytest.raises(OrganizationNotFoundException):
            await service.create(data, user)

    async def test_get_event_found(self) -> None:
        event = _make_event()
        event_repo = AsyncMock()
        event_repo.get_active_by_id.return_value = event

        service = self._make_service(event_repo=event_repo)
        result = await service.get(event.id)

        assert result is event

    async def test_get_event_not_found_raises(self) -> None:
        event_repo = AsyncMock()
        event_repo.get_active_by_id.return_value = None

        service = self._make_service(event_repo=event_repo)

        with pytest.raises(EventNotFoundException):
            await service.get(uuid4())

    async def test_update_event_success(self) -> None:
        event = _make_event()
        updated_event = _make_event(event_id=event.id)
        user = _make_user()

        event_repo = AsyncMock()
        event_repo.get_active_by_id.return_value = event
        event_repo.update.return_value = updated_event

        service = self._make_service(event_repo=event_repo)
        data = EventUpdate(title="Updated Event")
        result = await service.update(event.id, data, user)

        assert result is updated_event
        event_repo.update.assert_awaited_once()

    async def test_update_event_not_found_raises(self) -> None:
        event_repo = AsyncMock()
        event_repo.get_active_by_id.return_value = None

        service = self._make_service(event_repo=event_repo)
        data = EventUpdate(title="Updated Event")

        with pytest.raises(EventNotFoundException):
            await service.update(uuid4(), data, _make_user())

    async def test_delete_event_success(self) -> None:
        event = _make_event()
        user = _make_user()

        event_repo = AsyncMock()
        event_repo.get_active_by_id.return_value = event
        event_repo.delete_soft.return_value = event

        service = self._make_service(event_repo=event_repo)
        result = await service.delete(event.id, user)

        assert result is event
        event_repo.delete_soft.assert_awaited_once()

    async def test_delete_event_not_found_raises(self) -> None:
        event_repo = AsyncMock()
        event_repo.get_active_by_id.return_value = None

        service = self._make_service(event_repo=event_repo)

        with pytest.raises(EventNotFoundException):
            await service.delete(uuid4(), _make_user())

    async def test_list_events_success(self) -> None:
        org_id = uuid4()
        org = _make_organization(org_id=org_id)
        event = _make_event(org_id=org_id)

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = org
        event_repo = AsyncMock()
        event_repo.list_by_organization_and_range.return_value = (
            [event],
            PaginationMeta(page=1, page_size=10, total=1, pages=1),
        )

        service = self._make_service(event_repo=event_repo, org_repo=org_repo)
        start = datetime.now(UTC)
        end = start + timedelta(days=30)
        pagination = PaginationParams(page=1, page_size=10)
        items, meta = await service.list_events(org_id, start, end, pagination)

        assert items == [event]
        assert meta.total == 1
        event_repo.list_by_organization_and_range.assert_awaited_once()

    async def test_list_events_org_not_found_raises(self) -> None:
        org_id = uuid4()

        org_repo = AsyncMock()
        org_repo.get_active_by_id.return_value = None

        service = self._make_service(org_repo=org_repo)
        start = datetime.now(UTC)
        end = start + timedelta(days=30)
        pagination = PaginationParams(page=1, page_size=10)

        with pytest.raises(OrganizationNotFoundException):
            await service.list_events(org_id, start, end, pagination)


class TestEventSchemas:
    def test_event_create_multi_day_raises(self) -> None:
        start = datetime.now(UTC)
        end = start + timedelta(days=1)

        with pytest.raises(ValidationError):
            EventCreate(
                organization_id=uuid4(),
                title="Multi-day",
                start_time=start,
                end_time=end,
            )

    def test_event_create_same_day_ok(self) -> None:
        start = datetime.now(UTC)
        end = start + timedelta(hours=2)

        data = EventCreate(
            organization_id=uuid4(),
            title="Same-day",
            start_time=start,
            end_time=end,
        )

        assert data.start_time == start
        assert data.end_time == end

    def test_event_update_multi_day_raises(self) -> None:
        start = datetime.now(UTC)
        end = start + timedelta(days=1)

        with pytest.raises(ValidationError):
            EventUpdate(start_time=start, end_time=end)

    def test_event_update_same_day_ok(self) -> None:
        start = datetime.now(UTC)
        end = start + timedelta(hours=2)

        data = EventUpdate(start_time=start, end_time=end)

        assert data.start_time == start
        assert data.end_time == end
