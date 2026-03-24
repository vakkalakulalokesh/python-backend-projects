from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class TaskResult:
    success: bool
    output: Any
    error: str | None = None
    duration_ms: int = 0


class BaseTask(ABC):
    @abstractmethod
    async def execute(self, config: dict, input_data: dict | None = None) -> TaskResult:
        pass

    @property
    @abstractmethod
    def task_type(self) -> str:
        pass
