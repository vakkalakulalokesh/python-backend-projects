from __future__ import annotations

import asyncio
import time

from app.tasks.base import BaseTask, TaskResult


class DelayTask(BaseTask):
    @property
    def task_type(self) -> str:
        return "delay"

    async def execute(self, config: dict, input_data: dict | None = None) -> TaskResult:
        start = time.perf_counter()
        seconds = float(config.get("delay_seconds", 1))
        await asyncio.sleep(seconds)
        duration_ms = int((time.perf_counter() - start) * 1000)
        return TaskResult(success=True, output={"delayed_seconds": seconds}, duration_ms=duration_ms)
