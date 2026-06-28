import json
from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.core.redis import RedisManager


class Cache:
    @staticmethod
    def _serialize(value: Any) -> str:
        return json.dumps(value, default=Cache._json_default)

    @staticmethod
    def _deserialize(value: str | None) -> Any:
        if value is None:
            return None
        return json.loads(value)

    @staticmethod
    def _json_default(obj: Any) -> str:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return str(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    @classmethod
    async def get(cls, key: str) -> Any:
        redis = RedisManager.get()
        value = await redis.get(key)
        return cls._deserialize(value)

    @classmethod
    async def set(cls, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        redis = RedisManager.get()
        await redis.set(key, cls._serialize(value), ex=ttl_seconds)

    @classmethod
    async def delete(cls, key: str) -> None:
        redis = RedisManager.get()
        await redis.delete(key)

    @classmethod
    async def exists(cls, key: str) -> bool:
        redis = RedisManager.get()
        return bool(await redis.exists(key))
