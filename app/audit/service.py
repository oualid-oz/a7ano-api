import json
from uuid import UUID

from app.audit.models import AuditEvent
from app.audit.repository import AuditEventRepository
from app.audit.schemas import AuditEventCreate
from app.common.schemas import PaginationMeta, PaginationParams
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuditService:
    def __init__(self, repository: AuditEventRepository) -> None:
        self._repository = repository

    async def emit(self, data: AuditEventCreate) -> AuditEvent:
        logger.info(
            "Audit event emitted",
            extra={
                "actor_id": str(data.actor_id),
                "action": data.action,
                "resource_type": data.resource_type,
                "resource_id": data.resource_id,
                "organization_id": str(data.organization_id) if data.organization_id else None,
            },
        )
        meta_str = json.dumps(data.metadata_) if data.metadata_ else None
        event = AuditEvent(
            actor_id=data.actor_id,
            action=data.action,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
            organization_id=data.organization_id,
            ip_address=data.ip_address,
            user_agent=data.user_agent,
            metadata_=meta_str,
        )
        event = await self._repository.create(event)
        logger.info(
            "Audit event persisted",
            extra={"event_id": str(event.id), "action": event.action},
        )
        return event

    async def list_by_organization(
        self, org_id: UUID, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        logger.info(
            "Listing audit events by organization",
            extra={
                "org_id": str(org_id),
                "page": pagination.page,
                "page_size": pagination.page_size,
            },
        )
        events, meta = await self._repository.list_by_organization(org_id, pagination)
        logger.info("Audit list response", extra={"org_id": str(org_id), "total": meta.total})
        return events, meta

    async def list_by_actor(
        self, actor_id: UUID, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        logger.info(
            "Listing audit events by actor",
            extra={"actor_id": str(actor_id), "page": pagination.page},
        )
        events, meta = await self._repository.list_by_actor(actor_id, pagination)
        logger.info("Audit list response", extra={"actor_id": str(actor_id), "total": meta.total})
        return events, meta

    async def list_by_resource(
        self, resource_type: str, resource_id: str, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        logger.info(
            "Listing audit events by resource",
            extra={
                "resource_type": resource_type,
                "resource_id": resource_id,
                "page": pagination.page,
            },
        )
        events, meta = await self._repository.list_by_resource(
            resource_type, resource_id, pagination
        )
        logger.info(
            "Audit list response",
            extra={"resource_type": resource_type, "resource_id": resource_id, "total": meta.total},
        )
        return events, meta
