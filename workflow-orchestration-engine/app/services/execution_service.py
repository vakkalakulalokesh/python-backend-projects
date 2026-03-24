from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.cache.redis_client import RedisClient
from app.engine.executor import WorkflowExecutor
from app.engine.state_machine import ExecutionState, ExecutionStateMachine
from app.models.execution import TaskExecution, WorkflowExecution
from app.schemas.execution import (
    ExecutionListResponse,
    ExecutionResponse,
    ExecutionStats,
    TaskExecutionResponse,
    TaskLogEntry,
)
from app.workers.celery_app import celery_app


class ExecutionService:
    async def get_execution(self, db: AsyncSession, execution_pk: UUID) -> WorkflowExecution | None:
        result = await db.execute(
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.task_executions))
            .where(WorkflowExecution.id == execution_pk)
        )
        return result.scalar_one_or_none()

    async def list_executions(
        self,
        db: AsyncSession,
        workflow_id: UUID | None,
        status: str | None,
        page: int,
        size: int,
    ) -> ExecutionListResponse:
        page = max(1, page)
        size = min(100, max(1, size))
        cq = select(func.count()).select_from(WorkflowExecution)
        q = select(WorkflowExecution).options(selectinload(WorkflowExecution.task_executions))
        if workflow_id:
            cq = cq.where(WorkflowExecution.workflow_id == workflow_id)
            q = q.where(WorkflowExecution.workflow_id == workflow_id)
        if status:
            cq = cq.where(WorkflowExecution.status == status)
            q = q.where(WorkflowExecution.status == status)
        total_result = await db.execute(cq)
        total = int(total_result.scalar_one())
        q = q.order_by(WorkflowExecution.created_at.desc()).offset((page - 1) * size).limit(size)
        result = await db.execute(q)
        rows = list(result.scalars().unique().all())
        items = [self.to_response(e) for e in rows]
        return ExecutionListResponse(items=items, total=total, page=page, size=size)

    def to_response(self, e: WorkflowExecution) -> ExecutionResponse:
        tasks = [TaskExecutionResponse.model_validate(t) for t in sorted(e.task_executions, key=lambda x: x.created_at)]
        data = ExecutionResponse.model_validate(e)
        return data.model_copy(update={"task_executions": tasks})

    async def cancel_execution(self, db: AsyncSession, redis: Any, execution_pk: UUID) -> bool:
        ex = await self.get_execution(db, execution_pk)
        if ex is None:
            return False
        rc = redis if redis is not None else RedisClient.from_settings()
        need_close = redis is None
        if need_close:
            await rc.connect()
        try:
            executor = WorkflowExecutor(db, rc, None)
            await executor.cancel_execution(str(execution_pk))
            return True
        finally:
            if need_close:
                await rc.aclose()

    async def retry_execution(self, db: AsyncSession, redis: Any, execution_pk: UUID) -> bool:
        ex = await self.get_execution(db, execution_pk)
        if ex is None:
            return False
        sm = ExecutionStateMachine(ex.status)
        if sm.state in (ExecutionState.COMPLETED, ExecutionState.CANCELLED, ExecutionState.RUNNING):
            return False
        if sm.can_transition_to(ExecutionState.PENDING):
            sm.transition_to(ExecutionState.PENDING)
        ex.status = ExecutionState.PENDING.value
        ex.error = None
        ex.completed_at = None
        ex.output_data = None
        for te in ex.task_executions:
            if te.status == "failed":
                te.status = "pending"
                te.error = None
                te.output_data = None
                te.attempt = 1
                te.started_at = None
                te.completed_at = None
                te.duration_ms = None
        await db.commit()
        celery_app.send_task(
            "app.workers.workflow_worker.execute_workflow_task",
            args=[str(ex.id)],
        )
        return True

    async def get_logs(self, db: AsyncSession, execution_pk: UUID) -> list[TaskLogEntry]:
        ex = await self.get_execution(db, execution_pk)
        if ex is None:
            return []
        logs: list[TaskLogEntry] = []
        for te in sorted(ex.task_executions, key=lambda x: x.created_at):
            summary = None
            if te.output_data is not None:
                summary = str(te.output_data)[:500]
            logs.append(
                TaskLogEntry(
                    task_execution_id=te.id,
                    task_name=te.task_name,
                    task_type=te.task_type,
                    status=te.status,
                    attempt=te.attempt,
                    error=te.error,
                    output_summary=summary,
                )
            )
        return logs

    async def get_execution_stats(self, db: AsyncSession, workflow_id: UUID | None) -> ExecutionStats:
        q = select(WorkflowExecution)
        if workflow_id:
            q = q.where(WorkflowExecution.workflow_id == workflow_id)
        result = await db.execute(q.options(selectinload(WorkflowExecution.task_executions)))
        rows = list(result.scalars().unique().all())
        total = len(rows)
        by_status: dict[str, int] = {}
        durations: list[int] = []
        for e in rows:
            by_status[e.status] = by_status.get(e.status, 0) + 1
            if e.started_at and e.completed_at:
                ms = int((e.completed_at - e.started_at).total_seconds() * 1000)
                durations.append(ms)
        avg_ms = sum(durations) / len(durations) if durations else 0.0
        completed = by_status.get("completed", 0)
        success_rate = (completed / total) if total else 0.0
        recent = sorted(rows, key=lambda x: x.created_at, reverse=True)[:10]
        return ExecutionStats(
            total=total,
            by_status=by_status,
            avg_duration_ms=avg_ms,
            success_rate=success_rate,
            recent_executions=[self.to_response(e) for e in recent],
        )
