from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_redis_client
from app.cache.redis_client import RedisClient
from app.kafka_client import KafkaProducerClient
from app.models.database import get_db

DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_redis(request: Request) -> RedisClient:
    return get_redis_client()


RedisDep = Annotated[RedisClient, Depends(get_redis)]


def get_kafka_producer(request: Request) -> KafkaProducerClient | None:
    return getattr(request.app.state, "kafka_producer", None)


KafkaProducerDep = Annotated[
    KafkaProducerClient | None, Depends(get_kafka_producer)
]
