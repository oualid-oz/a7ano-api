from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.audit.router import router as audit_router
from app.auth.router import router as auth_router
from app.core.config import settings
from app.core.database import async_session_maker, close_db
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.core.redis import RedisManager
from app.core.router import router
from app.dms.router import router as dms_router
from app.memos.router import router as memos_router
from app.notifications.router import router as notifications_router
from app.organizations.router import router as organizations_router
from app.permissions.router import router as permissions_router
from app.permissions.service import seed_permissions_and_roles
from app.projects.router import router as projects_router
from app.scheduling.router import router as scheduling_router
from app.tasks.router import router as tasks_router
from app.teams.router import router as teams_router
from app.users.router import router as users_router
from app.vault.router import router as vault_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    with suppress(Exception):
        await RedisManager.connect()
    with suppress(Exception):
        async with async_session_maker() as session:
            await seed_permissions_and_roles(session)
            await session.commit()
    yield
    await RedisManager.disconnect()
    await close_db()


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url=f"{settings.api_prefix}/docs",
        redoc_url=f"{settings.api_prefix}/redoc",
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )
    register_middleware(app)
    register_exception_handlers(app)
    app.include_router(router, prefix=settings.api_prefix)
    app.include_router(auth_router, prefix=settings.api_prefix)
    app.include_router(users_router, prefix=settings.api_prefix)
    app.include_router(permissions_router, prefix=settings.api_prefix)
    app.include_router(organizations_router, prefix=settings.api_prefix)
    app.include_router(teams_router, prefix=settings.api_prefix)
    app.include_router(projects_router, prefix=settings.api_prefix)
    app.include_router(scheduling_router, prefix=settings.api_prefix)
    app.include_router(tasks_router, prefix=settings.api_prefix)
    app.include_router(memos_router, prefix=settings.api_prefix)
    app.include_router(vault_router, prefix=settings.api_prefix)
    app.include_router(audit_router, prefix=settings.api_prefix)
    app.include_router(notifications_router, prefix=settings.api_prefix)
    app.include_router(dms_router, prefix=settings.api_prefix)
    return app
