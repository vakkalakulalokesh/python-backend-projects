from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DbSession
from app.schemas.anomaly import (
    AnomalyAcknowledge,
    AnomalyListResponse,
    AnomalyResponse,
    AnomalyStats,
)
from app.services import anomaly_service

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.get("", response_model=AnomalyListResponse)
async def list_anomalies(
    db: DbSession,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    severity: str | None = None,
    status: str | None = None,
    detector: str | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> AnomalyListResponse:
    items, total = await anomaly_service.list_anomalies(
        db, page, size, severity, status, detector, start, end
    )
    return AnomalyListResponse(
        items=[AnomalyResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/stats", response_model=AnomalyStats)
async def anomaly_stats(db: DbSession) -> AnomalyStats:
    return await anomaly_service.get_stats(db)


@router.get("/{anomaly_id}", response_model=AnomalyResponse)
async def get_anomaly_detail(
    anomaly_id: UUID,
    db: DbSession,
) -> AnomalyResponse:
    rec = await anomaly_service.get_anomaly(db, anomaly_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="anomaly not found")
    return AnomalyResponse.model_validate(rec)


@router.patch("/{anomaly_id}/acknowledge", response_model=AnomalyResponse)
async def acknowledge(
    anomaly_id: UUID,
    body: AnomalyAcknowledge,
    db: DbSession,
) -> AnomalyResponse:
    rec = await anomaly_service.acknowledge_anomaly(
        db, anomaly_id, body.acknowledged_by
    )
    if rec is None:
        raise HTTPException(status_code=404, detail="anomaly not found")
    await db.commit()
    return AnomalyResponse.model_validate(rec)


@router.patch("/{anomaly_id}/resolve", response_model=AnomalyResponse)
async def resolve(
    anomaly_id: UUID,
    db: DbSession,
) -> AnomalyResponse:
    rec = await anomaly_service.resolve_anomaly(db, anomaly_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="anomaly not found")
    await db.commit()
    return AnomalyResponse.model_validate(rec)


@router.patch("/{anomaly_id}/false-positive", response_model=AnomalyResponse)
async def false_positive(
    anomaly_id: UUID,
    db: DbSession,
) -> AnomalyResponse:
    rec = await anomaly_service.mark_false_positive(db, anomaly_id)
    if rec is None:
        raise HTTPException(status_code=404, detail="anomaly not found")
    await db.commit()
    return AnomalyResponse.model_validate(rec)
