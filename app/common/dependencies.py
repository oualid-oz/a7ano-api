from collections.abc import Callable, Coroutine
from typing import Any, Protocol
from uuid import UUID

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.schemas import PaginationParams
from app.core.database import get_db


class RepositoryType(Protocol):
    def __init__(self, session: AsyncSession) -> None: ...


def get_pagination(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort: str | None = Query(None),
    search: str | None = Query(None),
) -> PaginationParams:
    return PaginationParams(
        page=page,
        page_size=page_size,
        sort=sort,
        search=search,
    )


def get_repository[T: RepositoryType](
    repository_class: type[T],
) -> Callable[[AsyncSession], Coroutine[Any, Any, T]]:
    async def _get_repository(
        session: AsyncSession = Depends(get_db),
    ) -> T:
        return repository_class(session)

    return _get_repository


def parse_uuid(value: str) -> UUID:
    return UUID(value)
