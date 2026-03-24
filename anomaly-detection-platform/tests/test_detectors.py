import numpy as np

from app.detectors.ewma import EWMADetector
from app.detectors.iqr import IQRDetector
from app.detectors.isolation_forest import IsolationForestDetector
from app.detectors.mad import MADDetector
from app.detectors.zscore import ZScoreDetector


def test_zscore_detects_outlier() -> None:
    d = ZScoreDetector(threshold=3.0)
    hist = [10.0, 10.1, 9.9, 10.0, 10.2, 9.8, 10.0, 10.1]
    r = d.detect(hist, 25.0)
    assert r.is_anomaly is True
    assert r.score > 0.5


def test_zscore_passes_normal() -> None:
    d = ZScoreDetector(threshold=3.0)
    hist = [10.0, 10.1, 9.9, 10.0, 10.2, 9.8, 10.0, 10.1]
    r = d.detect(hist, 10.05)
    assert r.is_anomaly is False


def test_iqr_detects_outlier() -> None:
    d = IQRDetector(multiplier=1.5)
    hist = list(np.linspace(10, 11, 30))
    r = d.detect([float(x) for x in hist], 50.0)
    assert r.is_anomaly is True


def test_mad_detects_outlier() -> None:
    d = MADDetector(threshold=3.5)
    hist = [10.0] * 20 + [10.1, 9.9, 10.05]
    r = d.detect(hist, 40.0)
    assert r.is_anomaly is True


def test_ewma_detects_drift() -> None:
    d = EWMADetector(span=5, sigma_threshold=2.0)
    base = [10.0 + 0.02 * i for i in range(40)]
    r = d.detect(base, 25.0)
    assert r.is_anomaly is True


def test_isolation_forest_detects_anomaly() -> None:
    d = IsolationForestDetector(contamination=0.1, random_state=0)
    rng = np.random.default_rng(0)
    normal = rng.normal(0, 0.1, 40).tolist()
    r = d.detect([float(x) for x in normal], 5.0)
    assert r.is_anomaly is True
