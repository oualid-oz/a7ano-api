from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.repository import AuditEventRepository
from app.audit.service import AuditService
from app.core.database import get_db


def get_audit_repository(
    session: AsyncSession = Depends(get_db),
) -> AuditEventRepository:
    return AuditEventRepository(session)


def get_audit_service(
    repo: AuditEventRepository = Depends(get_audit_repository),
) -> AuditService:
    return AuditService(repo)
