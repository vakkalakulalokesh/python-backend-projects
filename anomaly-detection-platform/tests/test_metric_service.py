import os
from datetime import datetime, timedelta, timezone

import pytest

from app.schemas.metric import MetricIngest, MetricQuery
from app.services import metric_service

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_INTEGRATION") != "1",
    reason="set RUN_INTEGRATION=1 with Postgres and Redis for this test",
)


@pytest.mark.asyncio
async def test_ingest_and_query(db_session, test_redis) -> None:
    now = datetime.now(timezone.utc)
    ingest = MetricIngest(
        source_name="test-svc",
        metric_name="cpu.util",
        value=42.5,
        unit="percent",
        timestamp=now,
    )
    point = await metric_service.ingest_metric(
        db_session, test_redis, ingest, kafka_producer=None
    )
    await db_session.commit()
    assert point.metric_name == "cpu.util"
    assert abs(point.value - 42.5) < 1e-6

    q = MetricQuery(
        source_name="test-svc",
        metric_name="cpu.util",
        start_time=now - timedelta(hours=1),
        end_time=now + timedelta(hours=1),
    )
    rows = await metric_service.query_metrics(db_session, q)
    assert len(rows) >= 1
    assert rows[-1].value == pytest.approx(42.5)
