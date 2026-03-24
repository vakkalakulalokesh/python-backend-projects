from datetime import datetime, timezone
from uuid import UUID

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.cache.redis_client import RedisClient
from app.kafka_client import KafkaProducerClient
from app.kafka_client.producer import publish_metric_event
from app.models.metric import MetricDataPoint, MetricSource
from app.schemas.metric import (
    MetricAggregation,
    MetricBatchIngest,
    MetricIngest,
    MetricQuery,
)
from app.services.detection_engine import run_detection


async def get_or_create_source(
    db: AsyncSession,
    name: str,
    source_type: str = "application",
) -> MetricSource:
    res = await db.execute(select(MetricSource).where(MetricSource.name == name))
    existing = res.scalar_one_or_none()
    if existing:
        return existing
    src = MetricSource(name=name, source_type=source_type, active=True)
    db.add(src)
    await db.flush()
    return src


async def create_source(
    db: AsyncSession,
    name: str,
    source_type: str,
    description: str | None,
    tags: dict | None,
) -> MetricSource:
    src = MetricSource(
        name=name,
        source_type=source_type,
        description=description,
        tags=tags,
        active=True,
    )
    db.add(src)
    await db.flush()
    return src


async def get_source(db: AsyncSession, source_id: UUID) -> MetricSource | None:
    res = await db.execute(select(MetricSource).where(MetricSource.id == source_id))
    return res.scalar_one_or_none()


async def list_sources(db: AsyncSession) -> list[MetricSource]:
    res = await db.execute(select(MetricSource).order_by(MetricSource.name))
    return list(res.scalars().all())


async def ingest_metric(
    db: AsyncSession,
    redis_client: RedisClient,
    data: MetricIngest,
    kafka_producer: KafkaProducerClient | None = None,
) -> MetricDataPoint:
    ts = data.timestamp or datetime.now(timezone.utc)
    source = await get_or_create_source(db, data.source_name)
    point = MetricDataPoint(
        source_id=source.id,
        metric_name=data.metric_name,
        value=data.value,
        unit=data.unit,
        tags=data.tags,
        timestamp=ts,
    )
    db.add(point)
    await db.flush()
    key = redis_client.sliding_window_key(str(source.id), data.metric_name)
    await redis_client.add_to_sliding_window(
        key, ts, data.value, settings.DETECTION_WINDOW_SIZE
    )
    payload = {
        "source_name": data.source_name,
        "metric_name": data.metric_name,
        "value": data.value,
        "unit": data.unit,
        "timestamp": ts.isoformat(),
    }
    if kafka_producer is not None:
        await publish_metric_event(
            kafka_producer,
            payload,
            key=data.source_name,
        )
    await run_detection(
        redis_client,
        db,
        data.source_name,
        data.metric_name,
        data.value,
        kafka_producer=kafka_producer,
    )
    return point


async def ingest_batch(
    db: AsyncSession,
    redis_client: RedisClient,
    data: MetricBatchIngest,
    kafka_producer: KafkaProducerClient | None = None,
) -> list[MetricDataPoint]:
    out: list[MetricDataPoint] = []
    for m in data.metrics:
        out.append(
            await ingest_metric(db, redis_client, m, kafka_producer=kafka_producer)
        )
    return out


async def query_metrics(
    db: AsyncSession, query: MetricQuery
) -> list[MetricDataPoint]:
    res = await db.execute(
        select(MetricDataPoint)
        .join(MetricSource)
        .where(
            MetricSource.name == query.source_name,
            MetricDataPoint.metric_name == query.metric_name,
            MetricDataPoint.timestamp >= query.start_time,
            MetricDataPoint.timestamp <= query.end_time,
        )
        .order_by(MetricDataPoint.timestamp)
    )
    return list(res.scalars().all())


async def get_aggregation(
    db: AsyncSession, query: MetricQuery
) -> MetricAggregation | None:
    stmt = (
        select(
            func.avg(MetricDataPoint.value),
            func.min(MetricDataPoint.value),
            func.max(MetricDataPoint.value),
            func.stddev_pop(MetricDataPoint.value),
            func.count(MetricDataPoint.id),
        )
        .join(MetricSource)
        .where(
            MetricSource.name == query.source_name,
            MetricDataPoint.metric_name == query.metric_name,
            MetricDataPoint.timestamp >= query.start_time,
            MetricDataPoint.timestamp <= query.end_time,
        )
    )
    row = (await db.execute(stmt)).one_or_none()
    if row is None or row[4] == 0:
        return None
    avg, vmin, vmax, std, cnt = row
    std_f = float(std) if std is not None else 0.0
    if np.isnan(std_f):
        std_f = 0.0
    return MetricAggregation(
        metric_name=query.metric_name,
        avg=float(avg),
        min=float(vmin),
        max=float(vmax),
        std_dev=std_f,
        count=int(cnt),
        period_start=query.start_time,
        period_end=query.end_time,
    )
