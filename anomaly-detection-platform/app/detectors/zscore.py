import numpy as np

from app.detectors.base import AnomalyDetector, DetectionResult


class ZScoreDetector(AnomalyDetector):
    def __init__(self, threshold: float = 3.0) -> None:
        self._threshold = threshold

    def name(self) -> str:
        return "zscore"

    def detect(self, values: list[float], current_value: float) -> DetectionResult:
        arr = np.array(values + [current_value], dtype=float)
        mean = float(np.mean(arr[:-1])) if len(arr) > 1 else float(current_value)
        std = float(np.std(arr[:-1], ddof=1)) if len(arr) > 2 else 0.0
        if std < 1e-12:
            z = 0.0
        else:
            z = abs(current_value - mean) / std
        score = min(1.0, z / (self._threshold * 2)) if self._threshold > 0 else 0.0
        is_anomaly = z > self._threshold
        deviation = abs(current_value - mean)
        return DetectionResult(
            is_anomaly=is_anomaly,
            score=score,
            expected_value=mean,
            actual_value=current_value,
            deviation=deviation,
            detector_name=self.name(),
            severity=self._calculate_severity(score) if is_anomaly else "low",
            reason=f"z={z:.4f} vs threshold {self._threshold}",
        )
