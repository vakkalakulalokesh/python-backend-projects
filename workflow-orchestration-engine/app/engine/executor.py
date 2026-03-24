from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.engine.dag import DAG, DAGNode
from app.engine.retry import get_retry_strategy
from app.engine.state_machine import ExecutionState, ExecutionStateMachine
from app.models.execution import TaskExecution, WorkflowExecution
from app.models.workflow import WorkflowDefinition
from app.schemas.workflow import DagDefinition
from app.tasks import get_task_class


class SupportsWebSocketBroadcast(Protocol):
    async def broadcast_execution(self, message: dict[str, Any]) -> None: ...


class WorkflowExecutor:
    def __init__(
        self,
        db_session: AsyncSession,
        redis_client: Any,
        ws_manager: SupportsWebSocketBroadcast | None = None,
    ) -> None:
        self.db = db_session
        self.redis = redis_client
        self.ws_manager = ws_manager
        self._sem = asyncio.Semaphore(settings.MAX_CONCURRENT_TASKS)

    async def _broadcast(self, payload: dict[str, Any]) -> None:
        await self.redis.publish_event(settings.WS_REDIS_CHANNEL, payload)
        if self.ws_manager is not None:
            await self.ws_manager.broadcast_execution(payload)

    async def execute_workflow(self, workflow_execution_id: str) -> None:
        exec_uuid = uuid.UUID(workflow_execution_id)
        result = await self.db.execute(
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.task_executions), selectinload(WorkflowExecution.workflow))
            .where(WorkflowExecution.id == exec_uuid)
        )
        execution = result.scalar_one_or_none()
        if execution is None:
            return
        wf = execution.workflow
        if wf is None:
            return
        dag_def = DagDefinition.model_validate(wf.dag_definition)
        dag = DAG(dag_def)
        sm = ExecutionStateMachine(execution.status)
        if sm.can_transition_to(ExecutionState.RUNNING):
            sm.transition_to(ExecutionState.RUNNING)
            execution.status = ExecutionState.RUNNING.value
            execution.started_at = datetime.now(timezone.utc)
            await self.db.commit()
        await self._broadcast(
            {
                "event": "execution_started",
                "execution_id": str(execution.id),
                "workflow_id": str(wf.id),
                "status": execution.status,
            }
        )
        completed: set[str] = set()
        skipped: set[str] = set()
        failed = False
        task_outputs: dict[str, Any] = {}
        for te in execution.task_executions:
            if te.status == "completed":
                completed.add(te.task_definition_id)
                if te.output_data is not None:
                    task_outputs[te.task_definition_id] = te.output_data
            elif te.status == "skipped":
                skipped.add(te.task_definition_id)
        glock = asyncio.Lock()

        async def refresh_execution() -> WorkflowExecution:
            await self.db.refresh(execution)
            return execution

        async def is_cancelled() -> bool:
            await refresh_execution()
            return execution.status == ExecutionState.CANCELLED.value

        async def run_node(node: DAGNode) -> None:
            nonlocal failed
            async with self._sem:
                if await is_cancelled():
                    return
                async with glock:
                    if node.task_id in completed or node.task_id in skipped:
                        return
                te = await self._get_or_create_task_execution(execution, node)
                workflow_input = execution.input_data or {}
                pred_ids = dag.predecessors(node.task_id)
                async with glock:
                    pred_outputs = {pid: task_outputs[pid] for pid in pred_ids if pid in task_outputs}
                merged_input = {**(workflow_input or {}), **pred_outputs, "tasks": pred_outputs}
                ok = await self._execute_task_with_retries(execution, te, node, merged_input, dag)
                async with glock:
                    if ok:
                        completed.add(node.task_id)
                        if te.output_data is not None:
                            task_outputs[node.task_id] = te.output_data
                    else:
                        failed = True
                if ok and node.task_type == "condition":
                    await self._apply_condition_branch_skips(node, te, dag, skipped, execution, glock)

        while len(completed) + len(skipped) < len(dag.nodes):
            if await is_cancelled():
                await self._broadcast(
                    {
                        "event": "execution_cancelled",
                        "execution_id": str(execution.id),
                        "status": execution.status,
                    }
                )
                return
            if failed:
                await self._fail_execution(execution)
                await self._broadcast(
                    {
                        "event": "execution_failed",
                        "execution_id": str(execution.id),
                        "status": execution.status,
                    }
                )
                return
            async with lock:
                for sid in dag.tasks_with_all_predecessors_skipped(completed, skipped):
                    skipped.add(sid)
                    ste = await self._get_or_create_task_execution(execution, dag.get_task(sid))
                    ste.status = "skipped"
                    ste.completed_at = datetime.now(timezone.utc)
                    await self.db.commit()
                    await self._broadcast(
                        {
                            "event": "task_skipped",
                            "execution_id": str(execution.id),
                            "task_id": sid,
                        }
                    )
                ready = dag.get_ready_tasks(completed, skipped, set())
                ready = [n for n in ready if n.task_id not in completed and n.task_id not in skipped]
            if not ready:
                if len(completed) + len(skipped) >= len(dag.nodes):
                    break
                await asyncio.sleep(0.05)
                continue
            await asyncio.gather(*[run_node(n) for n in ready])
            if failed:
                break

        if await is_cancelled():
            return
        if failed:
            return
        await self._complete_execution(execution, task_outputs)
        await self._broadcast(
            {
                "event": "execution_completed",
                "execution_id": str(execution.id),
                "status": execution.status,
            }
        )

    async def _apply_condition_branch_skips(
        self,
        node: DAGNode,
        te: TaskExecution,
        dag: DAG,
        skipped: set[str],
        execution: WorkflowExecution,
    ) -> None:
        out = te.output_data or {}
        chosen = out.get("next_task_id") or ""
        on_true = str(node.config.get("on_true") or "")
        on_false = str(node.config.get("on_false") or "")
        to_skip: list[str] = []
        if on_true and on_false:
            if out.get("result") is True:
                to_skip.append(on_false)
            else:
                to_skip.append(on_true)
        for sid in to_skip:
            if sid and sid in dag.all_task_ids():
                async with glock:
                    skipped.add(sid)
                ste = await self._get_or_create_task_execution(execution, dag.get_task(sid))
                ste.status = "skipped"
                ste.completed_at = datetime.now(timezone.utc)
                await self.db.commit()
                await self._broadcast(
                    {
                        "event": "task_skipped",
                        "execution_id": str(execution.id),
                        "task_id": sid,
                    }
                )

    async def _get_or_create_task_execution(self, execution: WorkflowExecution, node: DAGNode) -> TaskExecution:
        for te in execution.task_executions:
            if te.task_definition_id == node.task_id:
                return te
        max_attempts = node.retry_config.get("max_attempts", settings.MAX_RETRY_ATTEMPTS) if node.retry_config else settings.MAX_RETRY_ATTEMPTS
        te = TaskExecution(
            execution_id=execution.id,
            task_definition_id=node.task_id,
            task_name=node.task_name,
            task_type=node.task_type,
            status="pending",
            max_attempts=max(1, int(max_attempts)),
        )
        self.db.add(te)
        await self.db.flush()
        execution.task_executions.append(te)
        return te

    async def _execute_task_with_retries(
        self,
        execution: WorkflowExecution,
        te: TaskExecution,
        node: DAGNode,
        merged_input: dict[str, Any],
        dag: DAG,
    ) -> bool:
        strategy = get_retry_strategy(node.retry_config)
        while te.attempt <= te.max_attempts:
            if execution.status == ExecutionState.CANCELLED.value:
                return False
            ok = await self._execute_task_once(execution, te, node, merged_input)
            if ok:
                return True
            if te.attempt >= te.max_attempts:
                return False
            delay = strategy.get_delay(te.attempt)
            await asyncio.sleep(delay)
            te.attempt += 1
            te.status = "pending"
            await self.db.commit()
        return False

    async def _execute_task_once(
        self,
        execution: WorkflowExecution,
        te: TaskExecution,
        node: DAGNode,
        merged_input: dict[str, Any],
    ) -> bool:
        handler_cls = get_task_class(node.task_type)
        handler = handler_cls()
        now = datetime.now(timezone.utc)
        te.status = "running"
        te.started_at = now
        te.error = None
        await self.db.commit()
        await self._broadcast(
            {
                "event": "task_running",
                "execution_id": str(execution.id),
                "task_id": node.task_id,
                "attempt": te.attempt,
            }
        )
        timeout = node.timeout_seconds or settings.TASK_DEFAULT_TIMEOUT
        try:
            result = await asyncio.wait_for(
                handler.execute(node.config, merged_input),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            te.status = "failed"
            te.error = "Task timed out"
            te.completed_at = datetime.now(timezone.utc)
            te.duration_ms = int(timeout * 1000)
            await self.db.commit()
            await self._broadcast(
                {
                    "event": "task_failed",
                    "execution_id": str(execution.id),
                    "task_id": node.task_id,
                    "error": te.error,
                }
            )
            return False
        te.completed_at = datetime.now(timezone.utc)
        if te.started_at:
            delta = te.completed_at - te.started_at
            te.duration_ms = int(delta.total_seconds() * 1000)
        else:
            te.duration_ms = result.duration_ms
        if result.success:
            te.status = "completed"
            te.output_data = self._normalize_output(result.output)
            te.error = None
            await self.db.commit()
            await self._broadcast(
                {
                    "event": "task_completed",
                    "execution_id": str(execution.id),
                    "task_id": node.task_id,
                }
            )
            return True
        te.status = "failed"
        te.error = result.error or "Unknown error"
        te.output_data = self._normalize_output(result.output) if result.output is not None else None
        await self.db.commit()
        await self._broadcast(
            {
                "event": "task_failed",
                "execution_id": str(execution.id),
                "task_id": node.task_id,
                "error": te.error,
            }
        )
        return False

    def _normalize_output(self, output: Any) -> Any:
        if hasattr(output, "model_dump"):
            return output.model_dump()
        if isinstance(output, (str, int, float, bool, type(None))):
            return output
        if isinstance(output, dict):
            return output
        if isinstance(output, list):
            return output
        return str(output)

    async def _complete_execution(self, execution: WorkflowExecution, task_outputs: dict[str, Any]) -> None:
        sm = ExecutionStateMachine(execution.status)
        sm.transition_to(ExecutionState.COMPLETED)
        execution.status = ExecutionState.COMPLETED.value
        execution.completed_at = datetime.now(timezone.utc)
        execution.output_data = {"tasks": task_outputs}
        execution.error = None
        await self.db.commit()

    async def _fail_execution(self, execution: WorkflowExecution) -> None:
        sm = ExecutionStateMachine(execution.status)
        if sm.can_transition_to(ExecutionState.FAILED):
            sm.transition_to(ExecutionState.FAILED)
            execution.status = ExecutionState.FAILED.value
        execution.completed_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def cancel_execution(self, execution_id: str) -> None:
        exec_uuid = uuid.UUID(execution_id)
        result = await self.db.execute(
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.task_executions))
            .where(WorkflowExecution.id == exec_uuid)
        )
        execution = result.scalar_one_or_none()
        if execution is None:
            return
        sm = ExecutionStateMachine(execution.status)
        if sm.can_transition_to(ExecutionState.CANCELLED):
            sm.transition_to(ExecutionState.CANCELLED)
            execution.status = ExecutionState.CANCELLED.value
            execution.completed_at = datetime.now(timezone.utc)
        for te in execution.task_executions:
            if te.status in ("pending", "running"):
                te.status = "cancelled"
                te.completed_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self._broadcast(
            {
                "event": "execution_cancelled",
                "execution_id": str(execution.id),
                "status": execution.status,
            }
        )
