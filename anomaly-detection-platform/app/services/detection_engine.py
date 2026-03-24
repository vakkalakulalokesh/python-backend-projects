import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.cache.redis_client import RedisClient
from app.detectors import registry
from app.kafka_client import KafkaProducerClient
from app.kafka_client.producer import publish_anomaly_event
from app.models.anomaly import AlertRule, AnomalyRecord
from app.models.metric import MetricSource
from app.services import notification_service

logger = logging.getLogger(__name__)

_SEVERITY_RANK = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _severity_meets_threshold(severity: str, threshold: str) -> bool:
    return _SEVERITY_RANK.get(severity, 0) >= _SEVERITY_RANK.get(threshold, 99)


async def run_detection(
    redis_client: RedisClient,
    db: AsyncSession,
    source_name: str,
    metric_name: str,
    value: float,
    kafka_producer: KafkaProducerClient | None = None,
) -> None:
    res = await db.execute(
        select(MetricSource).where(MetricSource.name == source_name)
    )
    source = res.scalar_one_or_none()
    if source is None:
        return
    key = redis_client.sliding_window_key(str(source.id), metric_name)
    window = await redis_client.get_sliding_window(
        key, settings.DETECTION_WINDOW_SIZE
    )
    if not window:
        return
    current = float(window[-1])
    hist = [float(x) for x in window[:-1]]
    results = registry.detect_with_all(hist, current)
    rules_res = await db.execute(select(AlertRule).where(AlertRule.enabled.is_(True)))
    rules = list(rules_res.scalars().all())
    for det in results:
        if not det.is_anomaly:
            continue
        cooldown_key = f"cd:{source.id}:{metric_name}:{det.detector_name}"
        if await redis_client.check_cooldown(cooldown_key):
            continue
        rec = AnomalyRecord(
            source_id=source.id,
            metric_name=metric_name,
            detector_type=det.detector_name,
            severity=det.severity,
            score=det.score,
            expected_value=det.expected_value,
            actual_value=det.actual_value,
            deviation=det.deviation,
            context={"reason": det.reason},
            status="new",
        )
        db.add(rec)
        await db.flush()
        await redis_client.arm_cooldown(cooldown_key)
        payload: dict[str, Any] = {
            "anomaly_id": str(rec.id),
            "source_id": str(source.id),
            "source_name": source_name,
            "metric_name": metric_name,
            "detector": det.detector_name,
            "severity": det.severity,
            "score": det.score,
            "actual_value": det.actual_value,
        }
        if kafka_producer is not None:
            try:
                await publish_anomaly_event(
                    kafka_producer, payload, key=source_name
                )
            except Exception:
                logger.exception("failed to publish anomaly event")
        try:
            from app.api.routes.websocket import manager

            await manager.broadcast(
                {
                    "type": "anomaly",
                    "payload": payload,
                }
            )
        except Exception:
            logger.exception("websocket broadcast failed")
        matched: list[AlertRule] = []
        for rule in rules:
            if rule.source_id is not None and rule.source_id != source.id:
                continue
            if rule.metric_name is not None and rule.metric_name != metric_name:
                continue
            if rule.detector_type != det.detector_name:
                continue
            if not _severity_meets_threshold(det.severity, rule.severity_threshold):
                continue
            rule_cd = f"rulecd:{rule.id}:{source.id}:{metric_name}"
            if await redis_client.check_cooldown(rule_cd):
                continue
            matched.append(rule)
            await redis_client.arm_cooldown(rule_cd, rule.cooldown_seconds)
        for rule in matched:
            await notification_service.send_notification(
                db, rec, rule.notification_channels
            )
