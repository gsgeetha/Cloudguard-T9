from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from cloudguard.core.database import get_db
from cloudguard.models.policy_rule import PolicyRule
from cloudguard.schemas.policy_rule import (
    PolicyRuleCreate,
    PolicyRuleResponse,
)
from cloudguard.services.audit_service import create_audit_log

router = APIRouter(
    prefix="/api/v1/policies",
    tags=["Policies"],
)


@router.post(
    "",
    response_model=PolicyRuleResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_policy(
    policy: PolicyRuleCreate,
    db: Session = Depends(get_db),
) -> PolicyRule:
    existing_policy = db.scalar(
        select(PolicyRule).where(PolicyRule.name == policy.name)
    )

    if existing_policy:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Policy rule with this name already exists",
        )

    db_policy = PolicyRule(**policy.model_dump())

    db.add(db_policy)
    db.flush()

    create_audit_log(
        db,
        event_type="policy_created",
        entity_type="policy",
        entity_id=db_policy.id,
        actor="system",
        action="create_policy",
        details=f"Policy '{db_policy.name}' created",
    )

    db.commit()
    db.refresh(db_policy)

    return db_policy


@router.get(
    "",
    response_model=list[PolicyRuleResponse],
)
def list_policies(
    db: Session = Depends(get_db),
) -> list[PolicyRule]:
    return list(db.scalars(select(PolicyRule)).all())
