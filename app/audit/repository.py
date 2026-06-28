from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent
from app.common.repository import BaseRepository
from app.common.schemas import PaginationMeta, PaginationParams


class AuditEventRepository(BaseRepository[AuditEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditEvent)

    async def list_by_organization(
        self, organization_id: UUID, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        return await self.list(
            pagination,
            filters={"organization_id": organization_id},
            sort_field="created_at",
            sort_desc=True,
        )

    async def list_by_actor(
        self, actor_id: UUID, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        return await self.list(
            pagination,
            filters={"actor_id": actor_id},
            sort_field="created_at",
            sort_desc=True,
        )

    async def list_by_resource(
        self, resource_type: str, resource_id: str, pagination: PaginationParams
    ) -> tuple[list[AuditEvent], PaginationMeta]:
        return await self.list(
            pagination,
            filters={"resource_type": resource_type, "resource_id": resource_id},
            sort_field="created_at",
            sort_desc=True,
        )
