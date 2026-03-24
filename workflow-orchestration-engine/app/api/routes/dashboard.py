from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.models.execution import WorkflowExecution
from app.models.schedule import WorkflowSchedule
from app.models.workflow import WorkflowDefinition
from app.services.execution_service import ExecutionService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
async def dashboard_overview(db: AsyncSession = Depends(get_db)) -> dict:
    wf_count = await db.execute(select(func.count()).select_from(WorkflowDefinition).where(WorkflowDefinition.is_active.is_(True)))
    active_exec = await db.execute(
        select(func.count()).select_from(WorkflowExecution).where(WorkflowExecution.status.in_(["pending", "running"]))
    )
    stats = ExecutionService()
    s = await stats.get_execution_stats(db, None)
    now = datetime.now(timezone.utc)
    upcoming = await db.execute(
        select(WorkflowSchedule)
        .where(WorkflowSchedule.is_active.is_(True))
        .where(WorkflowSchedule.next_run_at.is_not(None))
        .order_by(WorkflowSchedule.next_run_at.asc())
        .limit(5)
    )
    up_rows = list(upcoming.scalars().all())
    return {
        "total_workflows": int(wf_count.scalar_one()),
        "active_executions": int(active_exec.scalar_one()),
        "success_rate": s.success_rate,
        "upcoming_schedules": [
            {
                "id": str(x.id),
                "name": x.name,
                "workflow_id": str(x.workflow_id),
                "next_run_at": x.next_run_at.isoformat() if x.next_run_at else None,
            }
            for x in up_rows
        ],
        "as_of": now.isoformat(),
    }


@router.get("/execution-timeline")
async def execution_timeline(
    workflow_id: Optional[UUID] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> List[dict]:
    q = select(WorkflowExecution).order_by(WorkflowExecution.created_at.desc()).limit(limit)
    if workflow_id:
        q = q.where(WorkflowExecution.workflow_id == workflow_id)
    result = await db.execute(q)
    rows = list(result.scalars().all())
    return [
        {
            "id": str(e.id),
            "execution_id": e.execution_id,
            "workflow_id": str(e.workflow_id),
            "status": e.status,
            "started_at": e.started_at.isoformat() if e.started_at else None,
            "completed_at": e.completed_at.isoformat() if e.completed_at else None,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in rows
    ]


@router.get("/workflow-health")
async def workflow_health(db: AsyncSession = Depends(get_db)) -> List[dict]:
    result = await db.execute(select(WorkflowDefinition).where(WorkflowDefinition.is_active.is_(True)))
    workflows = list(result.scalars().all())
    out: List[dict] = []
    stats = ExecutionService()
    for wf in workflows:
        s = await stats.get_execution_stats(db, wf.id)
        out.append(
            {
                "workflow_id": str(wf.id),
                "name": wf.name,
                "version": wf.version,
                "total_executions": s.total,
                "success_rate": s.success_rate,
                "by_status": s.by_status,
            }
        )
    return out
