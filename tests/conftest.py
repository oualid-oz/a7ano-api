import os
from collections.abc import AsyncGenerator, Generator

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

os.environ.setdefault("SECRET_KEY", "test-secret-key-32-bytes-long-for-local-use")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/omp")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

from app.common.models import Base
from app.core.application import create_app
from app.core.config import settings
from app.core.database import get_db


@pytest.fixture(scope="session")
def test_engine() -> Generator[AsyncEngine, None, None]:  # noqa: UP043
    async_url = settings.async_database_url or settings.database_url
    db_name = settings.database_url.split("/")[-1]
    test_url = async_url.replace(db_name, "test_omp")
    engine = create_async_engine(test_url, echo=False, future=True)
    yield engine
    engine.sync_engine.dispose()


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def setup_test_db(test_engine: AsyncEngine) -> AsyncGenerator[None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="session")
def app() -> FastAPI:
    return create_app()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    async with session_maker() as session:
        async with session.begin():
            yield session
        await session.rollback()


@pytest_asyncio.fixture
async def override_get_db(db_session: AsyncSession, app: FastAPI) -> AsyncGenerator[None]:
    async def _get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def any_user_password() -> str:
    return "SecureP@ssw0rd!"
