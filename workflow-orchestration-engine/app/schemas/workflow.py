from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class RetryConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    max_attempts: int = 3
    strategy: str = "fixed"
    delay_seconds: int = 5
    max_delay_seconds: int = 300


class TaskConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    name: str
    config: dict[str, Any] = Field(default_factory=dict)
    retry: Optional[RetryConfig] = None
    timeout_seconds: Optional[int] = None


class EdgeConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="allow")

    from_task: str = Field(alias="from")
    to_task: str = Field(alias="to")
    condition: Optional[str] = None


class DagDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    tasks: list[TaskConfig]
    edges: list[EdgeConfig] = Field(default_factory=list)


class WorkflowCreate(BaseModel):
    name: str
    description: Optional[str] = None
    dag_definition: DagDefinition
    input_schema: Optional[dict[str, Any]] = None
    created_by: str


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dag_definition: Optional[DagDefinition] = None
    input_schema: Optional[dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: Optional[str]
    version: int
    dag_definition: dict[str, Any]
    input_schema: Optional[dict[str, Any]]
    is_active: bool
    created_by: str
    created_at: Any
    updated_at: Any


class WorkflowListResponse(BaseModel):
    items: list[WorkflowResponse]
    total: int


class WorkflowTriggerRequest(BaseModel):
    input_data: Optional[dict[str, Any]] = None
    triggered_by: str = "manual"
    correlation_id: Optional[str] = None
