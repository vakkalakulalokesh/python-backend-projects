import numpy as np

from app.detectors.base import AnomalyDetector, DetectionResult


def _ewma_series(arr: np.ndarray, span: int) -> np.ndarray:
    alpha = 2.0 / (span + 1)
    out = np.empty_like(arr, dtype=float)
    if arr.size == 0:
        return out
    out[0] = arr[0]
    for i in range(1, arr.size):
        out[i] = alpha * arr[i] + (1.0 - alpha) * out[i - 1]
    return out


class EWMADetector(AnomalyDetector):
    def __init__(self, span: int = 20, sigma_threshold: float = 3.0) -> None:
        self._span = max(2, span)
        self._sigma_threshold = sigma_threshold

    def name(self) -> str:
        return "ewma"

    def detect(self, values: list[float], current_value: float) -> DetectionResult:
        hist = np.array(values, dtype=float)
        if hist.size < self._span:
            return DetectionResult(
                is_anomaly=False,
                score=0.0,
                expected_value=float(np.mean(hist)) if hist.size else current_value,
                actual_value=current_value,
                deviation=0.0,
                detector_name=self.name(),
                severity="low",
                reason="insufficient points for EWMA",
            )
        ew = _ewma_series(hist, self._span)
        expected = float(ew[-1])
        resid = hist - ew
        win = resid[-self._span :]
        std = float(np.std(win, ddof=1)) if win.size > 1 else 0.0
        if std < 1e-12:
            z = 0.0
        else:
            z = abs(current_value - expected) / std
        score = min(1.0, z / (self._sigma_threshold * 2))
        is_anomaly = z > self._sigma_threshold
        return DetectionResult(
            is_anomaly=is_anomaly,
            score=score,
            expected_value=expected,
            actual_value=current_value,
            deviation=abs(current_value - expected),
            detector_name=self.name(),
            severity=self._calculate_severity(score) if is_anomaly else "low",
            reason=f"EWMA deviation z={z:.4f}",
        )
