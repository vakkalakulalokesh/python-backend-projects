from __future__ import annotations

import time
from typing import Any

from app.tasks.base import BaseTask, TaskResult
from app.tasks.python_task import _ALLOWED_NAMES


class TransformTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "transform"

    async def execute(self, config: dict, input_data: dict | None = None) -> TaskResult:
        start = time.perf_counter()
        transformations: dict[str, str] = dict(config.get("transformations") or {})
        inp = input_data or {}
        out: dict[str, Any] = {}
        try:
            for key, expr in transformations.items():
                out[key] = eval(expr, {"__builtins__": {}}, {"input": inp, **_ALLOWED_NAMES})
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(success=True, output=out, duration_ms=duration_ms)
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(success=False, output=None, error=str(e), duration_ms=duration_ms)
