import numpy as np

from app.detectors.base import AnomalyDetector, DetectionResult


class MADDetector(AnomalyDetector):
    def __init__(self, threshold: float = 3.5) -> None:
        self._threshold = threshold

    def name(self) -> str:
        return "mad"

    def detect(self, values: list[float], current_value: float) -> DetectionResult:
        hist = np.array(values, dtype=float)
        if hist.size < 3:
            return DetectionResult(
                is_anomaly=False,
                score=0.0,
                expected_value=float(np.median(hist)) if hist.size else current_value,
                actual_value=current_value,
                deviation=0.0,
                detector_name=self.name(),
                severity="low",
                reason="insufficient history for MAD",
            )
        med = float(np.median(hist))
        mad = float(np.median(np.abs(hist - med)))
        if mad < 1e-12:
            mod_z = 0.0
        else:
            mod_z = abs(0.6745 * (current_value - med) / mad)
        score = min(1.0, mod_z / (self._threshold * 2)) if self._threshold > 0 else 0.0
        is_anomaly = mod_z > self._threshold
        return DetectionResult(
            is_anomaly=is_anomaly,
            score=score,
            expected_value=med,
            actual_value=current_value,
            deviation=abs(current_value - med),
            detector_name=self.name(),
            severity=self._calculate_severity(score) if is_anomaly else "low",
            reason=f"modified_z={mod_z:.4f} vs threshold {self._threshold}",
        )
