from __future__ import annotations

import asyncio
import uuid

from app.cache.redis_client import RedisClient
from app.engine.executor import WorkflowExecutor
from app.models.database import AsyncSessionLocal
from app.models.workflow import WorkflowDefinition
from app.schemas.workflow import WorkflowTriggerRequest
from app.services.workflow_service import WorkflowService
from app.workers.celery_app import celery_app


async def _run_execute(execution_uuid: str) -> None:
    redis_client = RedisClient.from_settings()
    await redis_client.connect()
    try:
        async with AsyncSessionLocal() as session:
            executor = WorkflowExecutor(session, redis_client, None)
            await executor.execute_workflow(execution_uuid)
    finally:
        await redis_client.aclose()


@celery_app.task(name="app.workers.workflow_worker.execute_workflow_task")
def execute_workflow_task(execution_id: str) -> None:
    asyncio.run(_run_execute(execution_id))


@celery_app.task(name="app.workers.workflow_worker.trigger_scheduled_workflow")
def trigger_scheduled_workflow(workflow_id: str, schedule_id: str, input_data: dict) -> None:
    async def _inner() -> None:
        async with AsyncSessionLocal() as session:
            wf = await session.get(WorkflowDefinition, uuid.UUID(workflow_id))
            if wf is None or not wf.is_active:
                return
            svc = WorkflowService()
            await svc.trigger_workflow(
                session,
                None,
                wf.id,
                WorkflowTriggerRequest(
                    input_data=input_data,
                    triggered_by="schedule",
                    correlation_id=schedule_id,
                ),
            )
            await session.commit()

    asyncio.run(_inner())
