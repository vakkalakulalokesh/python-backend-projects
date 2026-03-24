from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_redis
from app.cache.redis_client import RedisClient
from app.schemas.execution import ExecutionListResponse, ExecutionResponse, ExecutionStats, TaskLogEntry
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/executions", tags=["executions"])


@router.get("/stats", response_model=ExecutionStats)
async def execution_stats(
    workflow_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
) -> ExecutionStats:
    svc = ExecutionService()
    return await svc.get_execution_stats(db, workflow_id)


@router.get("", response_model=ExecutionListResponse)
async def list_executions(
    workflow_id: Optional[UUID] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ExecutionListResponse:
    svc = ExecutionService()
    return await svc.list_executions(db, workflow_id, status_filter, page, size)


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: UUID, db: AsyncSession = Depends(get_db)) -> ExecutionResponse:
    svc = ExecutionService()
    ex = await svc.get_execution(db, execution_id)
    if ex is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return svc.to_response(ex)


@router.post("/{execution_id}/cancel", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> None:
    svc = ExecutionService()
    ok = await svc.cancel_execution(db, redis, execution_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")


@router.post("/{execution_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_execution(
    execution_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> dict[str, str]:
    svc = ExecutionService()
    ok = await svc.retry_execution(db, redis, execution_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot retry execution")
    return {"execution_id": str(execution_id)}


@router.get("/{execution_id}/logs", response_model=List[TaskLogEntry])
async def execution_logs(execution_id: UUID, db: AsyncSession = Depends(get_db)) -> List[TaskLogEntry]:
    svc = ExecutionService()
    return await svc.get_logs(db, execution_id)
