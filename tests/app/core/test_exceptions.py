import httpx
import pytest
from fastapi import FastAPI, status
from httpx import AsyncClient

from app.core.exceptions import (
    ResourceNotFoundException,
    register_exception_handlers,
)


@pytest.mark.anyio
async def test_app_exception_handler() -> None:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/test")
    async def _route():
        raise ResourceNotFoundException(message="User not found.")

    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/test")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert data["success"] is False
    assert data["code"] == "RESOURCE_NOT_FOUND"
    assert data["message"] == "User not found."
