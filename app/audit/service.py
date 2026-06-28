import json
from uuid import UUID

from app.audit.models import AuditEvent
from app.audit.repository import AuditEventRepository
from app.audit.schemas import AuditEventCreate
from app.common.schemas import PaginationMeta, PaginationParams


class AuditService:
    def __init__(self, repository: AuditEventRepository) -> None:
        self._repository = repository

    async def emit(self, data: AuditEventCreate) -> AuditEvent:
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
        return await self._repository.create(event)

    async def list_by_organization(
        self, org_id: UUID, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        return await self._repository.list_by_organization(org_id, pagination)

    async def list_by_actor(
        self, actor_id: UUID, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        return await self._repository.list_by_actor(actor_id, pagination)

    async def list_by_resource(
        self, resource_type: str, resource_id: str, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        return await self._repository.list_by_resource(resource_type, resource_id, pagination)
