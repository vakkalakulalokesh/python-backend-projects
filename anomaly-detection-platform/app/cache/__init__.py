from app.cache.redis_client import RedisClient
from app.config import settings

_redis_client: RedisClient | None = None


def get_redis_client() -> RedisClient:
    if _redis_client is None:
        raise RuntimeError("Redis is not initialized")
    return _redis_client


async def init_redis() -> RedisClient:
    global _redis_client
    _redis_client = RedisClient(settings.REDIS_URL)
    await _redis_client.connect()
    return _redis_client


async def shutdown_redis() -> None:
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
