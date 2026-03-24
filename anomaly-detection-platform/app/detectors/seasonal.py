import numpy as np

from app.detectors.base import AnomalyDetector, DetectionResult


class SeasonalDecompositionDetector(AnomalyDetector):
    def __init__(self, period: int = 24, z_threshold: float = 3.0) -> None:
        self._period = max(2, period)
        self._z_threshold = z_threshold

    def name(self) -> str:
        return "seasonal"

    def detect(self, values: list[float], current_value: float) -> DetectionResult:
        hist = np.array(values, dtype=float)
        n = hist.size
        period = min(self._period, max(2, n // 3))
        if n < period * 2:
            return DetectionResult(
                is_anomaly=False,
                score=0.0,
                expected_value=float(np.mean(hist)) if n else current_value,
                actual_value=current_value,
                deviation=0.0,
                detector_name=self.name(),
                severity="low",
                reason="insufficient history for seasonal model",
            )
        window = max(3, period // 2 | 1)
        kernel = np.ones(window) / window
        trend = np.convolve(hist, kernel, mode="same")
        detrended = hist - trend
        seasonal = np.zeros(n)
        for i in range(n):
            phase = i % period
            mask = np.arange(n) % period == phase
            seasonal[i] = float(np.mean(detrended[mask]))
        residual_hist = hist - trend - seasonal
        last_trend = float(trend[-1])
        last_seasonal = float(seasonal[-1])
        expected = last_trend + last_seasonal
        resid_std = float(np.std(residual_hist, ddof=1)) if n > 2 else 0.0
        point_residual = current_value - expected
        if resid_std < 1e-12:
            z = 0.0
        else:
            z = abs(point_residual) / resid_std
        score = min(1.0, z / (self._z_threshold * 2))
        is_anomaly = z > self._z_threshold
        return DetectionResult(
            is_anomaly=is_anomaly,
            score=score,
            expected_value=expected,
            actual_value=current_value,
            deviation=abs(point_residual),
            detector_name=self.name(),
            severity=self._calculate_severity(score) if is_anomaly else "low",
            reason=f"seasonal residual z={z:.4f}",
        )
