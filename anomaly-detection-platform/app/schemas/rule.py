from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AlertRuleCreate(BaseModel):
    name: str
    source_id: UUID | None = None
    metric_name: str | None = None
    detector_type: str
    severity_threshold: str
    cooldown_seconds: int = 300
    notification_channels: list[dict[str, Any]] = Field(default_factory=list)


class AlertRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_id: UUID | None
    metric_name: str | None
    detector_type: str
    severity_threshold: str
    enabled: bool
    cooldown_seconds: int
    notification_channels: list[dict[str, Any]]
    created_at: datetime
    updated_at: datetime


class AlertRuleUpdate(BaseModel):
    source_id: UUID | None = None
    metric_name: str | None = None
    detector_type: str | None = None
    severity_threshold: str | None = None
    enabled: bool | None = None
    cooldown_seconds: int | None = None
    notification_channels: list[dict[str, Any]] | None = None
