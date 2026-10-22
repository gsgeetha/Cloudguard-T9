from datetime import datetime

from sqlalchemy.orm import Session

from cloudguard.models.finding import Finding
from cloudguard.models.policy_rule import PolicyRule
from cloudguard.models.remediation_action import RemediationAction


def request_remediation(
    db: Session,
    finding_id: int,
    requested_by: str,
) -> RemediationAction:
    finding = db.get(Finding, finding_id)

    if finding is None:
        raise ValueError("Finding not found")

    if finding.status == "closed":
        raise ValueError("Finding is already closed")

    policy = db.get(PolicyRule, finding.policy_rule_id)

    if policy is None:
        raise ValueError("Policy rule not found")

    # High-risk findings must wait for explicit approval.
    if requires_approval(finding.severity):
        remediation = RemediationAction(
            finding_id=finding.id,
            action_type="manual_approval_required",
            status="awaiting_approval",
            requested_by=requested_by,
            result_message="Remediation requires security approval",
        )

        db.add(remediation)
        db.commit()
        db.refresh(remediation)

        return remediation

    # MVP low-risk remediation: missing required tag.
    if policy.rule_type == "required_tag":
        remediation = RemediationAction(
            finding_id=finding.id,
            action_type="add_missing_tag",
            status="completed",
            requested_by=requested_by,
            result_message=(
                "Mock remediation completed: required Environment tag added"
            ),
            completed_at=datetime.utcnow(),
        )

        finding.status = "closed"

        db.add(remediation)
        db.commit()
        db.refresh(remediation)

        return remediation

    raise ValueError(
        f"No remediation is implemented for policy type '{policy.rule_type}'"
    )

def approve_remediation(
    db: Session,
    finding_id: int,
    approved_by: str,
) -> RemediationAction:
    finding = db.get(Finding, finding_id)

    if finding is None:
        raise ValueError("Finding not found")

    if finding.status == "closed":
        raise ValueError("Finding is already closed")

    remediation = (
        db.query(RemediationAction)
        .filter(
            RemediationAction.finding_id == finding_id,
            RemediationAction.status == "awaiting_approval",
        )
        .order_by(RemediationAction.requested_at.desc())
        .first()
    )

    if remediation is None:
        raise ValueError("No remediation is awaiting approval")

    remediation.status = "completed"
    remediation.approved_by = approved_by
    remediation.approved_at = datetime.utcnow()
    remediation.completed_at = datetime.utcnow()
    remediation.result_message = (
        "Mock high-risk remediation approved and completed"
    )

    finding.status = "closed"

    db.commit()
    db.refresh(remediation)

    return remediation

def requires_approval(severity: str) -> bool:
    return severity.casefold() in {"high", "critical"}