import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.anomaly import AnomalyRecord
from app.models.metric import MetricDataPoint
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def _cleanup_old_metrics_async() -> int:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.METRICS_RETENTION_DAYS
    )
    try:
        async with session_factory() as session:
            res = await session.execute(
                delete(MetricDataPoint).where(MetricDataPoint.timestamp < cutoff)
            )
            await session.commit()
            return res.rowcount or 0
    finally:
        await engine.dispose()


async def _cleanup_resolved_async() -> int:
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    session_factory = async_sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )
    cutoff = datetime.now(timezone.utc) - timedelta(
        days=settings.RESOLVED_ANOMALY_ARCHIVE_DAYS
    )
    try:
        async with session_factory() as session:
            res = await session.execute(
                delete(AnomalyRecord).where(
                    AnomalyRecord.status == "resolved",
                    AnomalyRecord.resolved_at.is_not(None),
                    AnomalyRecord.resolved_at < cutoff,
                )
            )
            await session.commit()
            return res.rowcount or 0
    finally:
        await engine.dispose()


@celery_app.task(name="app.workers.cleanup_task.cleanup_old_metrics")
def cleanup_old_metrics() -> int:
    try:
        return asyncio.run(_cleanup_old_metrics_async())
    except Exception:
        logger.exception("cleanup metrics failed")
        raise


@celery_app.task(name="app.workers.cleanup_task.cleanup_resolved_anomalies")
def cleanup_resolved_anomalies() -> int:
    try:
        return asyncio.run(_cleanup_resolved_async())
    except Exception:
        logger.exception("cleanup anomalies failed")
        raise
