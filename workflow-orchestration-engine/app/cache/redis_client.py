from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis


class RedisClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._client: aioredis.Redis | None = None

    @classmethod
    def from_settings(cls) -> "RedisClient":
        from app.config import settings

        return cls(settings.REDIS_URL)

    async def connect(self) -> None:
        if self._client is None:
            self._client = aioredis.from_url(self._url, decode_responses=True)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def raw(self) -> aioredis.Redis:
        if self._client is None:
            raise RuntimeError("Redis client not connected")
        return self._client

    async def acquire_lock(self, key: str, ttl: int = 30) -> bool:
        return await self.raw.set(f"lock:{key}", "1", nx=True, ex=ttl) is True

    async def release_lock(self, key: str) -> None:
        await self.raw.delete(f"lock:{key}")

    async def cache_get(self, key: str) -> str | None:
        return await self.raw.get(f"cache:{key}")

    async def cache_set(self, key: str, value: str, ttl: int = 300) -> None:
        await self.raw.set(f"cache:{key}", value, ex=ttl)

    async def publish_event(self, channel: str, data: dict[str, Any]) -> None:
        await self.raw.publish(channel, json.dumps(data))
