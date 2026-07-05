"""Integration tests for auth router endpoints."""
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_register_endpoint_returns_success_response(
    client: AsyncClient,
    override_get_db: None,
    setup_test_db: None,
) -> None:
    with patch("app.auth.service.RedisManager") as mock_rm:
        mock_rm.get.return_value = AsyncMock()

        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "register.test@example.com",
                "password": "SecureP@ssw0rd!",
                "full_name": "Register Test",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["code"] == "OK"
    assert "Registration successful" in data["message"]
    assert data["data"]["email"] == "register.test@example.com"
    assert data["data"]["full_name"] == "Register Test"
    assert "id" in data["data"]


@pytest.mark.anyio
async def test_login_endpoint_returns_tokens(
    client: AsyncClient,
    override_get_db: None,
    setup_test_db: None,
) -> None:
    email = "login.test@example.com"
    password = "SecureP@ssw0rd!"
    full_name = "Login Test"
    with patch("app.auth.service.RedisManager") as mock_rm:
        mock_rm.get.return_value = AsyncMock()

        await client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": password, "remember_me": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["access_token"]
    assert data["data"]["refresh_token"]
