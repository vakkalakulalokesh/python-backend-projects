import json
import uuid
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from app.config import settings


class RedisClient:
    def __init__(self, url: str) -> None:
        self._url = url
        self._r: redis.Redis | None = None

    async def connect(self) -> None:
        self._r = redis.from_url(
            self._url,
            encoding="utf-8",
            decode_responses=True,
        )

    async def close(self) -> None:
        if self._r is not None:
            await self._r.aclose()
            self._r = None

    def _client(self) -> redis.Redis:
        if self._r is None:
            raise RuntimeError("Redis client is not connected")
        return self._r

    def sliding_window_key(self, source_id: str, metric_name: str) -> str:
        return f"sw:{source_id}:{metric_name}"

    async def get_sliding_window(self, key: str, window_size: int) -> list[float]:
        r = self._client()
        raw = await r.zrange(key, -window_size, -1)
        out: list[float] = []
        for m in raw:
            try:
                payload = json.loads(m)
                out.append(float(payload["v"]))
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return out

    async def add_to_sliding_window(
        self, key: str, timestamp: datetime, value: float, window_size: int
    ) -> None:
        r = self._client()
        ts = timestamp.timestamp()
        member = json.dumps({"v": value, "t": ts, "id": str(uuid.uuid4())})
        await r.zadd(key, {member: ts})
        n = await r.zcard(key)
        if n > window_size:
            await r.zremrangebyrank(key, 0, n - window_size - 1)

    async def get_cached(self, key: str) -> Any | None:
        r = self._client()
        raw = await r.get(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw

    async def set_cached(self, key: str, value: Any, ttl: int) -> None:
        r = self._client()
        await r.setex(key, ttl, json.dumps(value))

    async def check_cooldown(self, key: str) -> bool:
        r = self._client()
        return bool(await r.exists(key))

    async def arm_cooldown(self, key: str, ttl_seconds: int | None = None) -> None:
        r = self._client()
        ttl = ttl_seconds if ttl_seconds is not None else settings.ANOMALY_COOLDOWN_SECONDS
        await r.setex(key, ttl, "1")

    async def increment_counter(self, key: str, ttl: int) -> int:
        r = self._client()
        val = await r.incr(key)
        if val == 1:
            await r.expire(key, ttl)
        return int(val)
