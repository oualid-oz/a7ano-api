from fastapi import Request

from app.core.config import settings
from app.core.exceptions import RateLimitException
from app.core.redis import RedisManager


def _build_key(identifier: str, suffix: str) -> str:
    return f"rate_limit:{identifier}:{suffix}"


class RateLimiter:
    def __init__(
        self,
        requests: int = settings.rate_limit_requests,
        window: int = settings.rate_limit_window_seconds,
    ) -> None:
        self.requests = requests
        self.window = window

    async def check(self, identifier: str, suffix: str) -> None:
        redis = RedisManager.get()
        key = _build_key(identifier, suffix)
        current = await redis.get(key)
        if current is None:
            await redis.set(key, 1, ex=self.window)
            return

        count = int(current)
        if count >= self.requests:
            raise RateLimitException()

        await redis.incr(key)

    async def __call__(self, request: Request) -> None:
        identifier = request.client.host if request.client else "unknown"
        await self.check(identifier, f"{request.method}:{request.url.path}")


class AuthenticatedRateLimiter(RateLimiter):
    async def __call__(self, request: Request) -> None:
        user_id = getattr(request.state, "user_id", None)
        identifier = (
            str(user_id) if user_id else (request.client.host if request.client else "unknown")
        )
        await self.check(identifier, f"{request.method}:{request.url.path}")


def rate_limit_dependency(
    requests: int = settings.rate_limit_requests,
    window: int = settings.rate_limit_window_seconds,
) -> RateLimiter:
    return RateLimiter(requests=requests, window=window)


def authenticated_rate_limit_dependency(
    requests: int = settings.rate_limit_requests,
    window: int = settings.rate_limit_window_seconds,
) -> AuthenticatedRateLimiter:
    return AuthenticatedRateLimiter(requests=requests, window=window)
