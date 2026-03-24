from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import TaskTemplate
from app.schemas.task import TaskTemplateCreate, TaskTemplateResponse, TaskTypeInfo
from app.tasks import TASK_REGISTRY


class TaskService:
    async def create_template(self, db: AsyncSession, data: TaskTemplateCreate) -> TaskTemplate:
        tpl = TaskTemplate(
            name=data.name,
            task_type=data.task_type,
            description=data.description,
            default_config=data.default_config,
        )
        db.add(tpl)
        await db.flush()
        await db.refresh(tpl)
        return tpl

    async def list_templates(self, db: AsyncSession) -> list[TaskTemplate]:
        result = await db.execute(select(TaskTemplate).order_by(TaskTemplate.created_at.desc()))
        return list(result.scalars().all())

    async def get_template(self, db: AsyncSession, template_id: UUID) -> TaskTemplate | None:
        return await db.get(TaskTemplate, template_id)

    def list_task_types(self) -> list[TaskTypeInfo]:
        meta: dict[str, tuple[str, list[str]]] = {
            "http": ("HTTP request via httpx", ["url", "method", "headers", "body", "expected_status_codes", "timeout"]),
            "python": ("Restricted Python expression over input", ["expression"]),
            "delay": ("asyncio sleep", ["delay_seconds"]),
            "condition": ("Boolean branch selection", ["condition", "on_true", "on_false"]),
            "transform": ("Per-key Python expressions", ["transformations"]),
        }
        out: list[TaskTypeInfo] = []
        for t, cls in TASK_REGISTRY.items():
            desc, fields = meta.get(t, (cls.__doc__ or t, []))
            out.append(TaskTypeInfo(type=t, description=desc, config_fields=fields))
        return out
