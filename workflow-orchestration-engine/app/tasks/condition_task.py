from __future__ import annotations

import time
from typing import Any

from app.tasks.base import BaseTask, TaskResult
from app.tasks.python_task import _ALLOWED_NAMES


class ConditionTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "condition"

    async def execute(self, config: dict, input_data: dict | None = None) -> TaskResult:
        start = time.perf_counter()
        condition = config.get("condition", "True")
        on_true = config.get("on_true", "")
        on_false = config.get("on_false", "")
        inp = input_data or {}
        try:
            result = bool(eval(condition, {"__builtins__": {}}, {"input": inp, **_ALLOWED_NAMES}))
            branch = "true_branch" if result else "false_branch"
            chosen = on_true if result else on_false
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(
                success=True,
                output={"result": result, "branch": branch, "next_task_id": chosen},
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(success=False, output=None, error=str(e), duration_ms=duration_ms)
