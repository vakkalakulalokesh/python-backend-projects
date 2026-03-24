from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MetricSourceCreate(BaseModel):
    name: str
    source_type: str
    description: str | None = None
    tags: dict[str, Any] | None = None


class MetricSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: str
    description: str | None
    tags: dict[str, Any] | None
    active: bool
    created_at: datetime
    updated_at: datetime


class MetricIngest(BaseModel):
    source_name: str
    metric_name: str
    value: float
    unit: str | None = None
    tags: dict[str, Any] | None = None
    timestamp: datetime | None = None


class MetricBatchIngest(BaseModel):
    metrics: list[MetricIngest] = Field(default_factory=list)


class MetricDataPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_id: UUID
    metric_name: str
    value: float
    unit: str | None
    tags: dict[str, Any] | None
    timestamp: datetime
    ingested_at: datetime


class MetricAggregation(BaseModel):
    metric_name: str
    avg: float
    min: float
    max: float
    std_dev: float
    count: int
    period_start: datetime
    period_end: datetime


class MetricQuery(BaseModel):
    source_name: str
    metric_name: str
    start_time: datetime
    end_time: datetime
    aggregation_interval: str | None = None
