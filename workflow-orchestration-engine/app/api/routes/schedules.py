from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_db
from app.schemas.schedule import ScheduleCreate, ScheduleResponse, ScheduleUpdate
from app.services.schedule_service import ScheduleService

router = APIRouter(prefix="/schedules", tags=["schedules"])


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    data: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    svc = ScheduleService()
    try:
        sched = await svc.create_schedule(db, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    return ScheduleResponse.model_validate(sched)


@router.get("", response_model=List[ScheduleResponse])
async def list_schedules(db: AsyncSession = Depends(get_db)) -> List[ScheduleResponse]:
    svc = ScheduleService()
    rows = await svc.list_schedules(db)
    return [ScheduleResponse.model_validate(r) for r in rows]


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    data: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
) -> ScheduleResponse:
    svc = ScheduleService()
    try:
        sched = await svc.update_schedule(db, schedule_id, data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if sched is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return ScheduleResponse.model_validate(sched)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    svc = ScheduleService()
    ok = await svc.delete_schedule(db, schedule_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")


@router.post("/{schedule_id}/toggle", response_model=ScheduleResponse)
async def toggle_schedule(schedule_id: UUID, db: AsyncSession = Depends(get_db)) -> ScheduleResponse:
    svc = ScheduleService()
    sched = await svc.toggle_schedule(db, schedule_id)
    if sched is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")
    return ScheduleResponse.model_validate(sched)
