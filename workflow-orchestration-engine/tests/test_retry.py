from __future__ import annotations

from app.engine.retry import (
    ExponentialBackoffStrategy,
    FixedRetryStrategy,
    LinearRetryStrategy,
)


def test_fixed_retry_constant_delay() -> None:
    s = FixedRetryStrategy(5.0)
    assert s.get_delay(1) == 5.0
    assert s.get_delay(3) == 5.0


def test_exponential_backoff_increasing_delay() -> None:
    s = ExponentialBackoffStrategy(base_delay=2.0, max_delay=300.0, jitter=False)
    assert s.get_delay(1) == 2.0
    assert s.get_delay(2) == 4.0
    assert s.get_delay(3) == 8.0


def test_exponential_max_cap() -> None:
    s = ExponentialBackoffStrategy(base_delay=100.0, max_delay=250.0, jitter=False)
    assert s.get_delay(5) == 250.0


def test_linear_retry() -> None:
    s = LinearRetryStrategy(initial_delay=5.0, increment=3.0, max_delay=100.0)
    assert s.get_delay(1) == 5.0
    assert s.get_delay(2) == 8.0
    assert s.get_delay(3) == 11.0
