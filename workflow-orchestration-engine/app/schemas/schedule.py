from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict
from uuid import UUID


class ScheduleCreate(BaseModel):
    workflow_id: UUID
    name: str
    cron_expression: str
    timezone: str = "UTC"
    is_active: bool = True
    input_data: Optional[dict[str, Any]] = None


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    input_data: Optional[dict[str, Any]] = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workflow_id: UUID
    name: str
    cron_expression: str
    timezone: str
    is_active: bool
    input_data: Optional[dict[str, Any]]
    last_run_at: Any
    next_run_at: Any
    total_runs: int
    created_at: Any
    updated_at: Any
