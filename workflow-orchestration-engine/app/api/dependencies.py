from collections.abc import AsyncGenerator
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis_client import RedisClient
from app.config import settings
from app.models.database import get_db

_redis: Optional[RedisClient] = None


async def get_redis() -> AsyncGenerator[RedisClient, None]:
    global _redis
    if _redis is None:
        _redis = RedisClient(settings.REDIS_URL)
        await _redis.connect()
    yield _redis
