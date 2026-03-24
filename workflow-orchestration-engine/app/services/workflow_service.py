from __future__ import annotations

import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.engine.dag import DAG
from app.models.execution import WorkflowExecution
from app.models.workflow import WorkflowDefinition
from app.schemas.workflow import DagDefinition, WorkflowCreate, WorkflowListResponse, WorkflowResponse, WorkflowTriggerRequest, WorkflowUpdate
from app.workers.celery_app import celery_app


class WorkflowService:
    async def create_workflow(self, db: AsyncSession, data: WorkflowCreate) -> WorkflowDefinition:
        DagDefinition.model_validate(data.dag_definition.model_dump())
        DAG(data.dag_definition)
        wf = WorkflowDefinition(
            name=data.name,
            description=data.description,
            dag_definition=data.dag_definition.model_dump(mode="json"),
            input_schema=data.input_schema,
            created_by=data.created_by,
            version=1,
        )
        db.add(wf)
        await db.flush()
        await db.refresh(wf)
        return wf

    async def get_workflow(self, db: AsyncSession, workflow_id: UUID) -> WorkflowDefinition | None:
        return await db.get(WorkflowDefinition, workflow_id)

    async def list_workflows(self, db: AsyncSession, page: int, size: int) -> WorkflowListResponse:
        page = max(1, page)
        size = min(100, max(1, size))
        total_result = await db.execute(
            select(func.count()).select_from(WorkflowDefinition).where(WorkflowDefinition.is_active.is_(True))
        )
        total = int(total_result.scalar_one())
        result = await db.execute(
            select(WorkflowDefinition)
            .where(WorkflowDefinition.is_active.is_(True))
            .order_by(WorkflowDefinition.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        items = list(result.scalars().all())
        return WorkflowListResponse(
            items=[WorkflowResponse.model_validate(i) for i in items],
            total=total,
        )

    async def update_workflow(self, db: AsyncSession, workflow_id: UUID, data: WorkflowUpdate) -> WorkflowDefinition | None:
        wf = await db.get(WorkflowDefinition, workflow_id)
        if wf is None:
            return None
        if data.name is not None:
            wf.name = data.name
        if data.description is not None:
            wf.description = data.description
        if data.dag_definition is not None:
            DAG(data.dag_definition)
            wf.dag_definition = data.dag_definition.model_dump(mode="json")
            wf.version = int(wf.version) + 1
        if data.input_schema is not None:
            wf.input_schema = data.input_schema
        if data.is_active is not None:
            wf.is_active = data.is_active
        await db.flush()
        await db.refresh(wf)
        return wf

    async def delete_workflow(self, db: AsyncSession, workflow_id: UUID) -> bool:
        wf = await db.get(WorkflowDefinition, workflow_id)
        if wf is None:
            return False
        wf.is_active = False
        await db.flush()
        return True

    async def trigger_workflow(
        self,
        db: AsyncSession,
        redis: Any,
        workflow_id: UUID,
        req: WorkflowTriggerRequest,
    ) -> WorkflowExecution:
        wf = await db.get(WorkflowDefinition, workflow_id)
        if wf is None or not wf.is_active:
            raise ValueError("Workflow not found or inactive")
        execution_id = f"ex-{uuid.uuid4().hex}"
        ex = WorkflowExecution(
            execution_id=execution_id,
            workflow_id=wf.id,
            status="pending",
            input_data=req.input_data,
            triggered_by=req.triggered_by,
            correlation_id=req.correlation_id,
        )
        db.add(ex)
        await db.flush()
        await db.refresh(ex)
        celery_app.send_task(
            "app.workers.workflow_worker.execute_workflow_task",
            args=[str(ex.id)],
        )
        return ex

    async def validate_dag(self, dag_definition: DagDefinition) -> dict[str, Any]:
        graph = DAG(dag_definition)
        return {"valid": True, "execution_order": graph.get_execution_order()}
