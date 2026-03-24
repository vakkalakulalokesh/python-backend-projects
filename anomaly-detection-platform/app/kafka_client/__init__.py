import json
from typing import Any, AsyncIterator

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer


class KafkaProducerClient:
    def __init__(self, bootstrap_servers: str) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: AIOKafkaProducer | None = None

    async def __aenter__(self) -> "KafkaProducerClient":
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def send(self, topic: str, key: str | None, value: dict[str, Any]) -> None:
        if self._producer is None:
            raise RuntimeError("producer not started")
        key_bytes = key.encode("utf-8") if key is not None else None
        await self._producer.send_and_wait(topic, value=value, key=key_bytes)


class KafkaConsumerClient:
    def __init__(
        self,
        bootstrap_servers: str,
        topics: list[str],
        group_id: str,
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._topics = topics
        self._group_id = group_id
        self._consumer: AIOKafkaConsumer | None = None

    async def __aenter__(self) -> "KafkaConsumerClient":
        self._consumer = AIOKafkaConsumer(
            *self._topics,
            bootstrap_servers=self._bootstrap_servers,
            group_id=self._group_id,
            enable_auto_commit=True,
            auto_offset_reset="earliest",
            value_deserializer=lambda b: json.loads(b.decode("utf-8")),
        )
        await self._consumer.start()
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None

    async def consume(self) -> AsyncIterator[dict[str, Any]]:
        if self._consumer is None:
            raise RuntimeError("consumer not started")
        async for msg in self._consumer:
            if msg.value is not None:
                yield msg.value
