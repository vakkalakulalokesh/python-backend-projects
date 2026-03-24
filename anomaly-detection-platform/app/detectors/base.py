from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectionResult:
    is_anomaly: bool
    score: float
    expected_value: Optional[float]
    actual_value: float
    deviation: float
    detector_name: str
    severity: str
    reason: str


class AnomalyDetector(ABC):
    @abstractmethod
    def detect(self, values: list[float], current_value: float) -> DetectionResult:
        pass

    @abstractmethod
    def name(self) -> str:
        pass

    def _calculate_severity(self, score: float) -> str:
        if score >= 0.9:
            return "critical"
        if score >= 0.7:
            return "high"
        if score >= 0.5:
            return "medium"
        return "low"
