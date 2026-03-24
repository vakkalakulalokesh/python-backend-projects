from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.task import TaskTemplateCreate, TaskTemplateResponse, TaskTypeInfo
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/templates", response_model=TaskTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    data: TaskTemplateCreate,
    db: AsyncSession = Depends(get_db),
) -> TaskTemplateResponse:
    svc = TaskService()
    tpl = await svc.create_template(db, data)
    return TaskTemplateResponse.model_validate(tpl)


@router.get("/templates", response_model=List[TaskTemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)) -> List[TaskTemplateResponse]:
    svc = TaskService()
    rows = await svc.list_templates(db)
    return [TaskTemplateResponse.model_validate(r) for r in rows]


@router.get("/templates/{template_id}", response_model=TaskTemplateResponse)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_db)) -> TaskTemplateResponse:
    svc = TaskService()
    tpl = await svc.get_template(db, template_id)
    if tpl is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")
    return TaskTemplateResponse.model_validate(tpl)


@router.get("/types", response_model=List[TaskTypeInfo])
async def list_task_types() -> List[TaskTypeInfo]:
    svc = TaskService()
    return svc.list_task_types()
