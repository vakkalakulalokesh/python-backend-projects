import logging
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import AnomalyRecord
from app.models.notification import AlertNotification

logger = logging.getLogger(__name__)


async def send_notification(
    db: AsyncSession,
    anomaly: AnomalyRecord,
    channels: list[dict[str, Any]],
) -> None:
    base_payload = {
        "anomaly_id": str(anomaly.id),
        "source_id": str(anomaly.source_id),
        "metric_name": anomaly.metric_name,
        "detector_type": anomaly.detector_type,
        "severity": anomaly.severity,
        "score": anomaly.score,
        "actual_value": anomaly.actual_value,
        "expected_value": anomaly.expected_value,
    }
    for ch in channels:
        ctype = str(ch.get("type", ch.get("channel", ""))).lower()
        if ctype == "webhook":
            url = ch.get("url")
            if not url:
                continue
            notif = AlertNotification(
                anomaly_id=anomaly.id,
                channel="webhook",
                payload={**base_payload, "target": url},
                status="pending",
            )
            db.add(notif)
            await db.flush()
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    r = await client.post(str(url), json=base_payload)
                    r.raise_for_status()
                notif.status = "sent"
                notif.error = None
                notif.sent_at = datetime.now(timezone.utc)
            except Exception as e:
                notif.status = "failed"
                notif.error = str(e)
                logger.warning("webhook notification failed: %s", e)
        elif ctype == "email":
            notif = AlertNotification(
                anomaly_id=anomaly.id,
                channel="email",
                payload={**base_payload, "to": ch.get("to")},
                status="sent",
            )
            db.add(notif)
            logger.info(
                "simulated email to %s for anomaly %s",
                ch.get("to"),
                anomaly.id,
            )
        elif ctype == "slack":
            notif = AlertNotification(
                anomaly_id=anomaly.id,
                channel="slack",
                payload={**base_payload, "channel": ch.get("channel_id")},
                status="sent",
            )
            db.add(notif)
            logger.info(
                "simulated slack notification for anomaly %s",
                anomaly.id,
            )
        else:
            notif = AlertNotification(
                anomaly_id=anomaly.id,
                channel=ctype or "unknown",
                payload=base_payload,
                status="failed",
                error="unsupported channel",
            )
            db.add(notif)
