from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import redis
from croniter import croniter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.schedule import WorkflowSchedule
from app.models.workflow import WorkflowDefinition


def compute_next_cron_run(cron_expression: str, after: datetime | None = None) -> datetime:
    base = after or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return croniter(cron_expression, base).get_next(datetime)


class WorkflowScheduler:
    def __init__(
        self,
        db_session_factory: async_sessionmaker[AsyncSession],
        redis_client: Any,
    ) -> None:
        self._session_factory = db_session_factory
        self._redis = redis_client

    def calculate_next_run(self, cron_expression: str, after: datetime | None = None) -> datetime:
        return compute_next_cron_run(cron_expression, after)

    async def check_and_trigger(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowSchedule).where(WorkflowSchedule.is_active.is_(True))
            )
            schedules = list(result.scalars().all())
            now = datetime.now(timezone.utc)
            for sched in schedules:
                lock_key = f"schedule_lock:{sched.id}"
                acquired = await self._redis.acquire_lock(lock_key, ttl=120)
                if not acquired:
                    continue
                try:
                    await session.refresh(sched)
                    if not sched.is_active:
                        continue
                    nxt = sched.next_run_at
                    if nxt is None:
                        nxt = compute_next_cron_run(sched.cron_expression, now)
                        sched.next_run_at = nxt
                        await session.commit()
                        continue
                    if nxt.tzinfo is None:
                        nxt = nxt.replace(tzinfo=timezone.utc)
                    if nxt > now:
                        continue
                    wf_result = await session.execute(
                        select(WorkflowDefinition).where(WorkflowDefinition.id == sched.workflow_id)
                    )
                    wf = wf_result.scalar_one_or_none()
                    if wf is None or not wf.is_active:
                        continue
                    self._enqueue_workflow_trigger(str(sched.workflow_id), str(sched.id), sched.input_data)
                    sched.last_run_at = now
                    sched.total_runs = int(sched.total_runs or 0) + 1
                    sched.next_run_at = compute_next_cron_run(sched.cron_expression, now)
                    await session.commit()
                finally:
                    await self._redis.release_lock(lock_key)

    def _enqueue_workflow_trigger(self, workflow_id: str, schedule_id: str, input_data: dict | None) -> None:
        from app.workers.celery_app import celery_app

        celery_app.send_task(
            "app.workers.workflow_worker.trigger_scheduled_workflow",
            args=[workflow_id, schedule_id, input_data or {}],
        )


def sync_acquire_lock(redis_url: str, key: str, ttl: int = 120) -> bool:
    r = redis.from_url(redis_url)
    try:
        return r.set(f"lock:{key}", "1", nx=True, ex=ttl) is True
    finally:
        r.close()


def sync_release_lock(redis_url: str, key: str) -> None:
    r = redis.from_url(redis_url)
    try:
        r.delete(f"lock:{key}")
    finally:
        r.close()
