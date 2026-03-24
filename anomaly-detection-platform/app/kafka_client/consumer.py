import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.config import settings
from app.kafka_client import KafkaConsumerClient
from app.models.database import async_session_factory
from app.services.detection_engine import run_detection

logger = logging.getLogger(__name__)


class MetricConsumer:
    def __init__(self, stop_event: asyncio.Event | None = None) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = stop_event or asyncio.Event()

    async def _loop(self) -> None:
        async with KafkaConsumerClient(
            settings.KAFKA_BOOTSTRAP_SERVERS,
            topics=["metrics.raw"],
            group_id="anomaly-detection-metrics",
        ) as consumer:
            async for payload in consumer.consume():
                if self._stop.is_set():
                    break
                try:
                    await self._handle(payload)
                except Exception:
                    logger.exception("metric consumer handle failed")

    async def _handle(self, payload: dict[str, Any]) -> None:
        source_name = str(payload.get("source_name", ""))
        metric_name = str(payload.get("metric_name", ""))
        value = float(payload.get("value", 0.0))
        if not source_name or not metric_name:
            return
        from app.cache import get_redis_client

        redis_client = get_redis_client()
        async with async_session_factory() as session:
            res = await session.execute(
                select(MetricSource).where(MetricSource.name == source_name)
            )
            source = res.scalar_one_or_none()
            if source is None:
                return
            ts_raw = payload.get("timestamp")
            if ts_raw:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            else:
                ts = datetime.now(timezone.utc)
            key = redis_client.sliding_window_key(str(source.id), metric_name)
            await redis_client.add_to_sliding_window(
                key, ts, value, settings.DETECTION_WINDOW_SIZE
            )
            await run_detection(redis_client, session, source_name, metric_name, value)
            await session.commit()

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
