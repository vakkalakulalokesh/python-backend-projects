from typing import Any

from app.kafka_client import KafkaProducerClient


async def publish_metric_event(
    producer: KafkaProducerClient,
    payload: dict[str, Any],
    key: str | None = None,
) -> None:
    await producer.send("metrics.ingested", key=key, value=payload)


async def publish_anomaly_event(
    producer: KafkaProducerClient,
    payload: dict[str, Any],
    key: str | None = None,
) -> None:
    await producer.send("anomalies.detected", key=key, value=payload)


async def publish_raw_metric(
    producer: KafkaProducerClient,
    payload: dict[str, Any],
    key: str | None = None,
) -> None:
    await producer.send("metrics.raw", key=key, value=payload)
