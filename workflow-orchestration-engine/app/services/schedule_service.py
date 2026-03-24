from __future__ import annotations

from uuid import UUID

from croniter import CroniterBadCronError, croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.scheduler import compute_next_cron_run
from app.models.schedule import WorkflowSchedule
from app.models.workflow import WorkflowDefinition
from app.schemas.schedule import ScheduleCreate, ScheduleUpdate


class ScheduleService:
    def _validate_cron(self, expr: str) -> None:
        try:
            croniter(expr)
        except CroniterBadCronError as e:
            raise ValueError(str(e)) from e

    async def create_schedule(self, db: AsyncSession, data: ScheduleCreate) -> WorkflowSchedule:
        wf = await db.get(WorkflowDefinition, data.workflow_id)
        if wf is None:
            raise ValueError("Workflow not found")
        self._validate_cron(data.cron_expression)
        sched = WorkflowSchedule(
            workflow_id=data.workflow_id,
            name=data.name,
            cron_expression=data.cron_expression,
            timezone=data.timezone,
            is_active=data.is_active,
            input_data=data.input_data,
        )
        sched.next_run_at = compute_next_cron_run(data.cron_expression)
        db.add(sched)
        await db.flush()
        await db.refresh(sched)
        return sched

    async def list_schedules(self, db: AsyncSession) -> list[WorkflowSchedule]:
        result = await db.execute(select(WorkflowSchedule).order_by(WorkflowSchedule.created_at.desc()))
        return list(result.scalars().all())

    async def update_schedule(self, db: AsyncSession, schedule_id: UUID, data: ScheduleUpdate) -> WorkflowSchedule | None:
        sched = await db.get(WorkflowSchedule, schedule_id)
        if sched is None:
            return None
        if data.name is not None:
            sched.name = data.name
        if data.cron_expression is not None:
            self._validate_cron(data.cron_expression)
            sched.cron_expression = data.cron_expression
            sched.next_run_at = compute_next_cron_run(data.cron_expression)
        if data.timezone is not None:
            sched.timezone = data.timezone
        if data.is_active is not None:
            sched.is_active = data.is_active
        if data.input_data is not None:
            sched.input_data = data.input_data
        await db.flush()
        await db.refresh(sched)
        return sched

    async def toggle_schedule(self, db: AsyncSession, schedule_id: UUID) -> WorkflowSchedule | None:
        sched = await db.get(WorkflowSchedule, schedule_id)
        if sched is None:
            return None
        sched.is_active = not sched.is_active
        await db.flush()
        await db.refresh(sched)
        return sched

    async def delete_schedule(self, db: AsyncSession, schedule_id: UUID) -> bool:
        sched = await db.get(WorkflowSchedule, schedule_id)
        if sched is None:
            return False
        await db.delete(sched)
        await db.flush()
        return True
