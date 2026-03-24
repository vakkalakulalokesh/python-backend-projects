from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db, get_redis
from app.cache.redis_client import RedisClient
from app.schemas.workflow import (
    DagDefinition,
    WorkflowCreate,
    WorkflowListResponse,
    WorkflowResponse,
    WorkflowTriggerRequest,
    WorkflowUpdate,
)
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.post("", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    data: WorkflowCreate,
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    svc = WorkflowService()
    try:
        wf = await svc.create_workflow(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return WorkflowResponse.model_validate(wf)


@router.get("", response_model=WorkflowListResponse)
async def list_workflows(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> WorkflowListResponse:
    svc = WorkflowService()
    return await svc.list_workflows(db, page, size)


@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)) -> WorkflowResponse:
    svc = WorkflowService()
    wf = await svc.get_workflow(db, workflow_id)
    if wf is None or not wf.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return WorkflowResponse.model_validate(wf)


@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: UUID,
    data: WorkflowUpdate,
    db: AsyncSession = Depends(get_db),
) -> WorkflowResponse:
    svc = WorkflowService()
    wf = await svc.update_workflow(db, workflow_id, data)
    if wf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    return WorkflowResponse.model_validate(wf)


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = WorkflowService()
    ok = await svc.delete_workflow(db, workflow_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")


@router.post("/{workflow_id}/trigger", status_code=status.HTTP_202_ACCEPTED)
async def trigger_workflow(
    workflow_id: UUID,
    body: Optional[WorkflowTriggerRequest] = None,
    db: AsyncSession = Depends(get_db),
    redis: RedisClient = Depends(get_redis),
) -> dict[str, str]:
    svc = WorkflowService()
    try:
        ex = await svc.trigger_workflow(db, redis, workflow_id, body or WorkflowTriggerRequest())
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return {"execution_id": str(ex.id), "execution_ref": ex.execution_id}


@router.get("/{workflow_id}/validate")
async def validate_workflow(workflow_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    svc = WorkflowService()
    wf = await svc.get_workflow(db, workflow_id)
    if wf is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found")
    dag = DagDefinition.model_validate(wf.dag_definition)
    return await svc.validate_dag(dag)
