from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationException

_argon2_hasher = PasswordHasher(
    time_cost=settings.argon2_time_cost,
    memory_cost=settings.argon2_memory_cost,
    parallelism=settings.argon2_parallelism,
)


def hash_password(password: str) -> str:
    return _argon2_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        _argon2_hasher.verify(hashed_password, password)
        return True
    except (VerifyMismatchError, InvalidHash):
        return False


def create_access_token(
    subject: UUID | str,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    to_encode = {
        "sub": str(subject),
        "type": "access",
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return cast(
        str,
        jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm),
    )


def create_refresh_token(
    subject: UUID | str,
    remember_me: bool = False,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    days = (
        settings.jwt_refresh_token_expire_days * 2
        if remember_me
        else settings.jwt_refresh_token_expire_days
    )
    expire = now + timedelta(days=days)
    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "iat": now,
        "exp": expire,
    }
    if extra_claims:
        to_encode.update(extra_claims)
    return cast(
        str,
        jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm),
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        return cast(
            dict[str, Any],
            jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm]),
        )
    except JWTError as exc:
        raise AuthenticationException("Invalid or expired token.") from exc
