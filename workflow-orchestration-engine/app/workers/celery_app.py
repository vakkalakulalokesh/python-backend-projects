from __future__ import annotations

import os
from datetime import timedelta

from celery import Celery

from app.config import settings

broker = os.environ.get("CELERY_BROKER_URL", settings.CELERY_BROKER_URL)

celery_app = Celery(
    "workflow_engine",
    broker=broker,
    backend=broker,
    include=["app.workers.workflow_worker", "app.workers.schedule_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "check-schedules": {
            "task": "app.workers.schedule_worker.check_schedules",
            "schedule": timedelta(seconds=settings.SCHEDULE_CHECK_INTERVAL),
        }
    },
)
