from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from app.api.dependencies import DbSession
from app.models.anomaly import AnomalyRecord
from app.models.metric import MetricDataPoint, MetricSource
from app.schemas.dashboard import DashboardOverview

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview", response_model=DashboardOverview)
async def dashboard_overview(db: DbSession) -> DashboardOverview:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_ago = now - timedelta(hours=1)

    total_sources = int(
        (await db.execute(select(func.count()).select_from(MetricSource))).scalar_one()
    )
    active_sources = int(
        (
            await db.execute(
                select(func.count()).select_from(MetricSource).where(
                    MetricSource.active.is_(True)
                )
            )
        ).scalar_one()
    )
    total_today = int(
        (
            await db.execute(
                select(func.count()).select_from(AnomalyRecord).where(
                    AnomalyRecord.detected_at >= day_start
                )
            )
        ).scalar_one()
    )
    critical = int(
        (
            await db.execute(
                select(func.count()).select_from(AnomalyRecord).where(
                    AnomalyRecord.detected_at >= day_start,
                    AnomalyRecord.severity == "critical",
                )
            )
        ).scalar_one()
    )
    ingested = int(
        (
            await db.execute(
                select(func.count()).select_from(MetricDataPoint).where(
                    MetricDataPoint.ingested_at >= hour_ago
                )
            )
        ).scalar_one()
    )
    top_rows = await db.execute(
        select(MetricSource.name, func.count(AnomalyRecord.id).label("c"))
        .join(AnomalyRecord, AnomalyRecord.source_id == MetricSource.id)
        .where(AnomalyRecord.detected_at >= day_start)
        .group_by(MetricSource.name)
        .order_by(func.count(AnomalyRecord.id).desc())
        .limit(5)
    )
    top_anomalous = [
        {"source_name": str(n), "count": int(c)} for n, c in top_rows
    ]
    det_rows = await db.execute(
        select(AnomalyRecord.detector_type, func.count().label("c"))
        .where(AnomalyRecord.detected_at >= day_start)
        .group_by(AnomalyRecord.detector_type)
    )
    det_perf: dict[str, Any] = {
        str(d): {"anomalies_today": int(c)} for d, c in det_rows
    }
    return DashboardOverview(
        total_sources=total_sources,
        active_sources=active_sources,
        total_anomalies_today=total_today,
        critical_anomalies=critical,
        metrics_ingested_last_hour=ingested,
        top_anomalous_sources=top_anomalous,
        detector_performance=det_perf,
    )


@router.get("/top-anomalous")
async def top_anomalous(
    db: DbSession,
    limit: int = Query(10, ge=1, le=50),
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await db.execute(
        select(MetricSource.name, func.count(AnomalyRecord.id).label("c"))
        .join(AnomalyRecord, AnomalyRecord.source_id == MetricSource.id)
        .where(AnomalyRecord.detected_at >= day_start)
        .group_by(MetricSource.name)
        .order_by(func.count(AnomalyRecord.id).desc())
        .limit(limit)
    )
    return [{"source_name": str(n), "count": int(c)} for n, c in rows]


@router.get("/detector-performance")
async def detector_performance(db: DbSession) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    rows = await db.execute(
        select(AnomalyRecord.detector_type, func.count().label("c"))
        .where(AnomalyRecord.detected_at >= day_start)
        .group_by(AnomalyRecord.detector_type)
    )
    return {str(d): {"anomalies_today": int(c)} for d, c in rows}


@router.get("/timeline")
async def timeline(
    db: DbSession,
    hours: int = Query(24, ge=1, le=168),
) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    rows = await db.execute(
        select(
            func.date_trunc("hour", AnomalyRecord.detected_at).label("bucket"),
            func.count().label("c"),
        )
        .where(AnomalyRecord.detected_at >= start)
        .group_by(func.date_trunc("hour", AnomalyRecord.detected_at))
        .order_by(func.date_trunc("hour", AnomalyRecord.detected_at))
    )
    out: list[dict[str, Any]] = []
    for b, c in rows:
        ts = b.isoformat() if hasattr(b, "isoformat") else str(b)
        out.append({"timestamp": ts, "count": int(c)})
    return out
