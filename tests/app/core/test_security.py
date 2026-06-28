from uuid import uuid4

import pytest

from app.core.exceptions import AuthenticationException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.mark.anyio
class TestPasswordSecurity:
    def test_password_hash_and_verify(self) -> None:
        password = "SecureP@ssw0rd!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True
        assert verify_password("wrong-password", hashed) is False


@pytest.mark.anyio
class TestTokenSecurity:
    def test_access_token_encode_decode(self) -> None:
        user_id = uuid4()
        token = create_access_token(user_id)
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "access"

    def test_refresh_token_encode_decode(self) -> None:
        user_id = uuid4()
        token = create_refresh_token(user_id, remember_me=True)
        payload = decode_token(token)
        assert payload["sub"] == str(user_id)
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self) -> None:
        with pytest.raises(AuthenticationException):
            decode_token("invalid-token")
