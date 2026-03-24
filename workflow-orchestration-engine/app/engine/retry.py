from __future__ import annotations

from abc import ABC, abstractmethod
import random


class RetryStrategy(ABC):
    @abstractmethod
    def get_delay(self, attempt: int) -> float:
        pass


class FixedRetryStrategy(RetryStrategy):
    def __init__(self, delay_seconds: float = 5.0) -> None:
        self.delay = delay_seconds

    def get_delay(self, attempt: int) -> float:
        return self.delay


class ExponentialBackoffStrategy(RetryStrategy):
    def __init__(self, base_delay: float = 2.0, max_delay: float = 300.0, jitter: bool = True) -> None:
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def get_delay(self, attempt: int) -> float:
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        if self.jitter:
            delay *= 0.5 + random.random()
        return delay


class LinearRetryStrategy(RetryStrategy):
    def __init__(self, initial_delay: float = 5.0, increment: float = 5.0, max_delay: float = 300.0) -> None:
        self.initial_delay = initial_delay
        self.increment = increment
        self.max_delay = max_delay

    def get_delay(self, attempt: int) -> float:
        return min(self.initial_delay + self.increment * (attempt - 1), self.max_delay)


def get_retry_strategy(config: dict | None) -> RetryStrategy:
    if not config:
        return FixedRetryStrategy()
    strategy = config.get("strategy", "fixed")
    if strategy == "exponential":
        return ExponentialBackoffStrategy(
            base_delay=float(config.get("delay_seconds", 2.0)),
            max_delay=float(config.get("max_delay_seconds", 300.0)),
        )
    if strategy == "linear":
        d = float(config.get("delay_seconds", 5.0))
        return LinearRetryStrategy(initial_delay=d, increment=d, max_delay=float(config.get("max_delay_seconds", 300.0)))
    return FixedRetryStrategy(delay_seconds=float(config.get("delay_seconds", 5.0)))
