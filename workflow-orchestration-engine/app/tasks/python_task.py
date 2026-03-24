from __future__ import annotations

import time
from typing import Any

from app.tasks.base import BaseTask, TaskResult


_ALLOWED_NAMES: dict[str, Any] = {
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "round": round,
    "sorted": sorted,
    "enumerate": enumerate,
    "zip": zip,
    "dict": dict,
    "list": list,
    "tuple": tuple,
    "set": set,
    "True": True,
    "False": False,
    "None": None,
}


class PythonTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "python"

    async def execute(self, config: dict, input_data: dict | None = None) -> TaskResult:
        start = time.perf_counter()
        expr = config.get("expression", "input")
        inp = input_data or {}
        try:
            out = eval(expr, {"__builtins__": {}}, {"input": inp, **_ALLOWED_NAMES})
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(success=True, output=out, duration_ms=duration_ms)
        except Exception as e:
            duration_ms = int((time.perf_counter() - start) * 1000)
            return TaskResult(success=False, output=None, error=str(e), duration_ms=duration_ms)
