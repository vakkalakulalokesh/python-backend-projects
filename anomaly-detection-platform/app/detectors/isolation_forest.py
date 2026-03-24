import numpy as np
from sklearn.ensemble import IsolationForest

from app.detectors.base import AnomalyDetector, DetectionResult


class IsolationForestDetector(AnomalyDetector):
    def __init__(self, contamination: float = 0.05, random_state: int = 42) -> None:
        self._contamination = contamination
        self._random_state = random_state

    def name(self) -> str:
        return "isolation_forest"

    def detect(self, values: list[float], current_value: float) -> DetectionResult:
        hist = np.array(values, dtype=float).reshape(-1, 1)
        if hist.shape[0] < 8:
            return DetectionResult(
                is_anomaly=False,
                score=0.0,
                expected_value=float(np.mean(hist)) if hist.size else current_value,
                actual_value=current_value,
                deviation=0.0,
                detector_name=self.name(),
                severity="low",
                reason="insufficient history for isolation forest",
            )
        clf = IsolationForest(
            contamination=min(self._contamination, 0.5),
            random_state=self._random_state,
        )
        clf.fit(hist)
        cur = np.array([[current_value]])
        pred = int(clf.predict(cur)[0])
        raw = float(clf.decision_function(cur)[0])
        score = float(1.0 / (1.0 + np.exp(raw * 4)))
        is_anomaly = pred == -1
        expected = float(np.mean(hist))
        return DetectionResult(
            is_anomaly=is_anomaly,
            score=score if is_anomaly else min(score, 0.3),
            expected_value=expected,
            actual_value=current_value,
            deviation=abs(current_value - expected),
            detector_name=self.name(),
            severity=self._calculate_severity(score) if is_anomaly else "low",
            reason=f"isolation score={raw:.4f}",
        )
