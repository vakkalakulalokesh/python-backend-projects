from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    metric_name: str
    detector_type: str
    severity: str
    score: float
    expected_value: float | None
    actual_value: float
    deviation: float
    context: dict[str, Any] | None
    status: str
    acknowledged_by: str | None
    resolved_at: datetime | None
    detected_at: datetime
    created_at: datetime


class AnomalyListResponse(BaseModel):
    items: list[AnomalyResponse]
    total: int
    page: int
    size: int


class AnomalyAcknowledge(BaseModel):
    acknowledged_by: str


class DailyAnomalyCount(BaseModel):
    date: str
    count: int


class AnomalyStats(BaseModel):
    total: int
    by_severity: dict[str, int]
    by_detector: dict[str, int]
    by_status: dict[str, int]
    trend: list[DailyAnomalyCount] = Field(default_factory=list)
