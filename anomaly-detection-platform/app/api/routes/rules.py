from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select

from app.api.dependencies import DbSession
from app.models.anomaly import AlertRule
from app.schemas.rule import AlertRuleCreate, AlertRuleResponse, AlertRuleUpdate

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=AlertRuleResponse, status_code=201)
async def create_rule(body: AlertRuleCreate, db: DbSession) -> AlertRuleResponse:
    rule = AlertRule(
        name=body.name,
        source_id=body.source_id,
        metric_name=body.metric_name,
        detector_type=body.detector_type,
        severity_threshold=body.severity_threshold,
        cooldown_seconds=body.cooldown_seconds,
        notification_channels=body.notification_channels,
        enabled=True,
    )
    db.add(rule)
    try:
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="could not create rule",
        )
    return AlertRuleResponse.model_validate(rule)


@router.get("", response_model=list[AlertRuleResponse])
async def list_rules(db: DbSession) -> list[AlertRuleResponse]:
    res = await db.execute(select(AlertRule).order_by(AlertRule.name))
    return [AlertRuleResponse.model_validate(r) for r in res.scalars().all()]


@router.get("/{rule_id}", response_model=AlertRuleResponse)
async def get_rule(rule_id: UUID, db: DbSession) -> AlertRuleResponse:
    res = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    return AlertRuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=AlertRuleResponse)
async def update_rule(
    rule_id: UUID,
    body: AlertRuleUpdate,
    db: DbSession,
) -> AlertRuleResponse:
    res = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    data = body.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(rule, k, v)
    await db.commit()
    return AlertRuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: UUID, db: DbSession) -> None:
    res = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    await db.execute(delete(AlertRule).where(AlertRule.id == rule_id))
    await db.commit()


@router.post("/{rule_id}/toggle", response_model=AlertRuleResponse)
async def toggle_rule(rule_id: UUID, db: DbSession) -> AlertRuleResponse:
    res = await db.execute(select(AlertRule).where(AlertRule.id == rule_id))
    rule = res.scalar_one_or_none()
    if rule is None:
        raise HTTPException(status_code=404, detail="rule not found")
    rule.enabled = not rule.enabled
    await db.commit()
    return AlertRuleResponse.model_validate(rule)
