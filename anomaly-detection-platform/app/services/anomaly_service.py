from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anomaly import AnomalyRecord
from app.schemas.anomaly import AnomalyStats, DailyAnomalyCount


async def list_anomalies(
    db: AsyncSession,
    page: int,
    size: int,
    severity: str | None = None,
    status: str | None = None,
    detector: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> tuple[list[AnomalyRecord], int]:
    stmt = select(AnomalyRecord)
    count_stmt = select(func.count()).select_from(AnomalyRecord)
    if severity:
        stmt = stmt.where(AnomalyRecord.severity == severity)
        count_stmt = count_stmt.where(AnomalyRecord.severity == severity)
    if status:
        stmt = stmt.where(AnomalyRecord.status == status)
        count_stmt = count_stmt.where(AnomalyRecord.status == status)
    if detector:
        stmt = stmt.where(AnomalyRecord.detector_type == detector)
        count_stmt = count_stmt.where(AnomalyRecord.detector_type == detector)
    if start:
        stmt = stmt.where(AnomalyRecord.detected_at >= start)
        count_stmt = count_stmt.where(AnomalyRecord.detected_at >= start)
    if end:
        stmt = stmt.where(AnomalyRecord.detected_at <= end)
        count_stmt = count_stmt.where(AnomalyRecord.detected_at <= end)
    total = int((await db.execute(count_stmt)).scalar_one())
    stmt = (
        stmt.order_by(AnomalyRecord.detected_at.desc())
        .offset(max(page - 1, 0) * size)
        .limit(size)
    )
    rows = await db.execute(stmt)
    return list(rows.scalars().all()), total


async def get_anomaly(db: AsyncSession, anomaly_id: UUID) -> AnomalyRecord | None:
    res = await db.execute(
        select(AnomalyRecord).where(AnomalyRecord.id == anomaly_id)
    )
    return res.scalar_one_or_none()


async def acknowledge_anomaly(
    db: AsyncSession, anomaly_id: UUID, acknowledged_by: str
) -> AnomalyRecord | None:
    rec = await get_anomaly(db, anomaly_id)
    if rec is None:
        return None
    rec.status = "acknowledged"
    rec.acknowledged_by = acknowledged_by
    return rec


async def resolve_anomaly(db: AsyncSession, anomaly_id: UUID) -> AnomalyRecord | None:
    rec = await get_anomaly(db, anomaly_id)
    if rec is None:
        return None
    rec.status = "resolved"
    rec.resolved_at = datetime.now(timezone.utc)
    return rec


async def mark_false_positive(
    db: AsyncSession, anomaly_id: UUID
) -> AnomalyRecord | None:
    rec = await get_anomaly(db, anomaly_id)
    if rec is None:
        return None
    rec.status = "false_positive"
    return rec


async def get_stats(db: AsyncSession) -> AnomalyStats:
    total = int(
        (await db.execute(select(func.count()).select_from(AnomalyRecord))).scalar_one()
    )
    by_sev: dict[str, int] = {}
    for row in await db.execute(
        select(AnomalyRecord.severity, func.count())
        .group_by(AnomalyRecord.severity)
    ):
        by_sev[str(row[0])] = int(row[1])
    by_det: dict[str, int] = {}
    for row in await db.execute(
        select(AnomalyRecord.detector_type, func.count())
        .group_by(AnomalyRecord.detector_type)
    ):
        by_det[str(row[0])] = int(row[1])
    by_stat: dict[str, int] = {}
    for row in await db.execute(
        select(AnomalyRecord.status, func.count()).group_by(AnomalyRecord.status)
    ):
        by_stat[str(row[0])] = int(row[1])
    start = datetime.now(timezone.utc).date() - timedelta(days=13)
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    trend_rows = await db.execute(
        select(
            func.date(AnomalyRecord.detected_at).label("d"),
            func.count().label("c"),
        )
        .where(AnomalyRecord.detected_at >= start_dt)
        .group_by(func.date(AnomalyRecord.detected_at))
        .order_by(func.date(AnomalyRecord.detected_at))
    )
    trend: list[DailyAnomalyCount] = []
    for d, c in trend_rows:
        ds = d.isoformat() if isinstance(d, date) else str(d)
        trend.append(DailyAnomalyCount(date=ds, count=int(c)))
    return AnomalyStats(
        total=total,
        by_severity=by_sev,
        by_detector=by_det,
        by_status=by_stat,
        trend=trend,
    )
