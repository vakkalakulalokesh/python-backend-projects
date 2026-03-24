from typing import Any

from pydantic import BaseModel, Field


class DashboardOverview(BaseModel):
    total_sources: int
    active_sources: int
    total_anomalies_today: int
    critical_anomalies: int
    metrics_ingested_last_hour: int
    top_anomalous_sources: list[dict[str, Any]] = Field(default_factory=list)
    detector_performance: dict[str, Any] = Field(default_factory=dict)
