from typing import cast

import redis.asyncio as redis

from app.core.config import settings


class RedisManager:
    _pool: redis.Redis | None = None

    @classmethod
    async def connect(cls) -> redis.Redis:
        cls._pool = cast(
            redis.Redis,
            redis.from_url(settings.redis_url, decode_responses=True),  # type: ignore[no-untyped-call]
        )
        return cls._pool

    @classmethod
    async def disconnect(cls) -> None:
        if cls._pool is not None:
            await cls._pool.close()
            cls._pool = None

    @classmethod
    def get(cls) -> redis.Redis:
        if cls._pool is None:
            raise RuntimeError("Redis connection has not been initialized.")
        return cls._pool
