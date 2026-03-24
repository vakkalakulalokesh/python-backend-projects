from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID


class TaskTemplateCreate(BaseModel):
    name: str
    task_type: str
    description: Optional[str] = None
    default_config: dict[str, Any] = Field(default_factory=dict)


class TaskTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    task_type: str
    description: Optional[str]
    default_config: dict[str, Any]
    created_at: Any


class TaskTypeInfo(BaseModel):
    type: str
    description: str
    config_fields: list[str]
