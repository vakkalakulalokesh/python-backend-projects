from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "anomaly_detection",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
    include=["app.workers.detection_task", "app.workers.cleanup_task"],
)

celery_app.conf.beat_schedule = {
    "cleanup-old-metrics-daily": {
        "task": "app.workers.cleanup_task.cleanup_old_metrics",
        "schedule": crontab(hour=3, minute=0),
    },
    "cleanup-resolved-anomalies-weekly": {
        "task": "app.workers.cleanup_task.cleanup_resolved_anomalies",
        "schedule": crontab(day_of_week=0, hour=4, minute=0),
    },
}
celery_app.conf.timezone = "UTC"
