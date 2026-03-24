import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.cache.redis_client import RedisClient
from app.config import settings
from app.models.metric import MetricDataPoint, MetricSource
from app.services.detection_engine import run_detection
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _run_batch_detection_async() -> int:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    redis_client = RedisClient(settings.REDIS_URL)
    await redis_client.connect()
    processed = 0
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=15)
        async with session_factory() as session:
            res = await session.execute(
                select(MetricDataPoint, MetricSource.name)
                .join(MetricSource)
                .where(MetricDataPoint.ingested_at >= cutoff)
                .order_by(MetricDataPoint.ingested_at.desc())
                .limit(500)
            )
            rows = res.all()
            for point, source_name in rows:
                await run_detection(
                    redis_client,
                    session,
                    str(source_name),
                    point.metric_name,
                    float(point.value),
                    kafka_producer=None,
                )
                processed += 1
            await session.commit()
    finally:
        await redis_client.close()
        await engine.dispose()
    return processed


@celery_app.task(name="app.workers.detection_task.run_batch_detection")
def run_batch_detection() -> int:
    try:
        return asyncio.run(_run_batch_detection_async())
    except Exception:
        logger.exception("batch detection failed")
        raise
