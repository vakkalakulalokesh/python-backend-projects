from __future__ import annotations

from app.tasks.base import BaseTask, TaskResult
from app.tasks.condition_task import ConditionTask
from app.tasks.delay_task import DelayTask
from app.tasks.http_task import HttpTask
from app.tasks.python_task import PythonTask
from app.tasks.transform_task import TransformTask

TASK_REGISTRY: dict[str, type[BaseTask]] = {
    "http": HttpTask,
    "python": PythonTask,
    "delay": DelayTask,
    "condition": ConditionTask,
    "transform": TransformTask,
}


def get_task_class(task_type: str) -> type[BaseTask]:
    if task_type not in TASK_REGISTRY:
        raise ValueError(f"Unknown task type: {task_type}")
    return TASK_REGISTRY[task_type]
