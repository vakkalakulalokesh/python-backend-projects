from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import DbSession, KafkaProducerDep, RedisDep
from app.schemas.metric import (
    MetricAggregation,
    MetricBatchIngest,
    MetricDataPointResponse,
    MetricIngest,
    MetricQuery,
    MetricSourceCreate,
    MetricSourceResponse,
)
from app.services import metric_service

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.post("/ingest", response_model=MetricDataPointResponse)
async def ingest_single(
    body: MetricIngest,
    db: DbSession,
    redis: RedisDep,
    kafka: KafkaProducerDep,
) -> MetricDataPointResponse:
    point = await metric_service.ingest_metric(db, redis, body, kafka_producer=kafka)
    await db.commit()
    return MetricDataPointResponse.model_validate(point)


@router.post("/ingest/batch", response_model=list[MetricDataPointResponse])
async def ingest_batch(
    body: MetricBatchIngest,
    db: DbSession,
    redis: RedisDep,
    kafka: KafkaProducerDep,
) -> list[MetricDataPointResponse]:
    points = await metric_service.ingest_batch(db, redis, body, kafka_producer=kafka)
    await db.commit()
    return [MetricDataPointResponse.model_validate(p) for p in points]


@router.get("/query", response_model=list[MetricDataPointResponse])
async def query_metrics(
    db: DbSession,
    source_name: str = Query(...),
    metric_name: str = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
) -> list[MetricDataPointResponse]:
    from datetime import datetime

    q = MetricQuery(
        source_name=source_name,
        metric_name=metric_name,
        start_time=datetime.fromisoformat(start_time.replace("Z", "+00:00")),
        end_time=datetime.fromisoformat(end_time.replace("Z", "+00:00")),
    )
    rows = await metric_service.query_metrics(db, q)
    return [MetricDataPointResponse.model_validate(r) for r in rows]


@router.get("/aggregation", response_model=MetricAggregation)
async def aggregation(
    db: DbSession,
    source_name: str = Query(...),
    metric_name: str = Query(...),
    start_time: str = Query(...),
    end_time: str = Query(...),
) -> MetricAggregation:
    from datetime import datetime

    q = MetricQuery(
        source_name=source_name,
        metric_name=metric_name,
        start_time=datetime.fromisoformat(start_time.replace("Z", "+00:00")),
        end_time=datetime.fromisoformat(end_time.replace("Z", "+00:00")),
    )
    agg = await metric_service.get_aggregation(db, q)
    if agg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="no data for aggregation window",
        )
    return agg


@router.post("/sources", response_model=MetricSourceResponse, status_code=201)
async def create_metric_source(
    body: MetricSourceCreate,
    db: DbSession,
) -> MetricSourceResponse:
    try:
        src = await metric_service.create_source(
            db,
            body.name,
            body.source_type,
            body.description,
            body.tags,
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    return MetricSourceResponse.model_validate(src)


@router.get("/sources", response_model=list[MetricSourceResponse])
async def list_metric_sources(db: DbSession) -> list[MetricSourceResponse]:
    rows = await metric_service.list_sources(db)
    return [MetricSourceResponse.model_validate(r) for r in rows]


@router.get("/sources/{source_id}", response_model=MetricSourceResponse)
async def get_metric_source(
    source_id: UUID,
    db: DbSession,
) -> MetricSourceResponse:
    src = await metric_service.get_source(db, source_id)
    if src is None:
        raise HTTPException(status_code=404, detail="source not found")
    return MetricSourceResponse.model_validate(src)
