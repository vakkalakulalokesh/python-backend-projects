from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class TaskExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: UUID
    task_definition_id: str
    task_name: str
    task_type: str
    status: str
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    error: Optional[str]
    attempt: int
    max_attempts: int
    started_at: Any
    completed_at: Any
    duration_ms: Optional[int]
    created_at: Any


class ExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    execution_id: str
    workflow_id: UUID
    status: str
    input_data: Optional[dict[str, Any]]
    output_data: Optional[dict[str, Any]]
    error: Optional[str]
    started_at: Any
    completed_at: Any
    created_at: Any
    triggered_by: str
    correlation_id: Optional[str]
    task_executions: list[TaskExecutionResponse] = Field(default_factory=list)


class ExecutionListResponse(BaseModel):
    items: list[ExecutionResponse]
    total: int
    page: int
    size: int


class ExecutionStats(BaseModel):
    total: int
    by_status: dict[str, int]
    avg_duration_ms: float
    success_rate: float
    recent_executions: list[ExecutionResponse]


class TaskLogEntry(BaseModel):
    task_execution_id: UUID
    task_name: str
    task_type: str
    status: str
    attempt: int
    error: Optional[str]
    output_summary: Optional[str]
