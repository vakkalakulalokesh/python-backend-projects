from app.config import settings
from app.detectors.base import AnomalyDetector, DetectionResult
from app.detectors.ewma import EWMADetector
from app.detectors.iqr import IQRDetector
from app.detectors.isolation_forest import IsolationForestDetector
from app.detectors.mad import MADDetector
from app.detectors.seasonal import SeasonalDecompositionDetector
from app.detectors.zscore import ZScoreDetector


class DetectorRegistry:
    def __init__(self) -> None:
        self._detectors: dict[str, AnomalyDetector] = {
            "zscore": ZScoreDetector(threshold=settings.ZSCORE_THRESHOLD),
            "iqr": IQRDetector(multiplier=settings.IQR_MULTIPLIER),
            "mad": MADDetector(),
            "ewma": EWMADetector(span=settings.EWMA_SPAN),
            "isolation_forest": IsolationForestDetector(),
            "seasonal": SeasonalDecompositionDetector(),
        }

    def get_detector(self, name: str) -> AnomalyDetector:
        if name not in self._detectors:
            raise KeyError(f"unknown detector: {name}")
        return self._detectors[name]

    def get_all_detectors(self) -> list[AnomalyDetector]:
        return list(self._detectors.values())

    def detect_with_all(
        self, values: list[float], current_value: float
    ) -> list[DetectionResult]:
        return [
            d.detect(values, current_value) for d in self.get_all_detectors()
        ]


registry = DetectorRegistry()

__all__ = [
    "AnomalyDetector",
    "DetectionResult",
    "DetectorRegistry",
    "registry",
]
