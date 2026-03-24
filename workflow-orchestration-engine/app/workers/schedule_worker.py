from __future__ import annotations

import asyncio

from app.cache.redis_client import RedisClient
from app.engine.scheduler import WorkflowScheduler
from app.models.database import AsyncSessionLocal
from app.workers.celery_app import celery_app


async def _check() -> None:
    redis_client = RedisClient.from_settings()
    await redis_client.connect()
    try:
        scheduler = WorkflowScheduler(AsyncSessionLocal, redis_client)
        await scheduler.check_and_trigger()
    finally:
        await redis_client.aclose()


@celery_app.task(name="app.workers.schedule_worker.check_schedules")
def check_schedules() -> None:
    asyncio.run(_check())
