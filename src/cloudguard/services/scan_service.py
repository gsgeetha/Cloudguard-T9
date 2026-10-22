from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from cloudguard.azure.mock_inventory import load_mock_resources
from cloudguard.models.finding import Finding
from cloudguard.models.policy_rule import PolicyRule
from cloudguard.models.scan import Scan
from cloudguard.models.subscription import Subscription
from cloudguard.policies.required_tag import evaluate_required_tag
from cloudguard.policies.risky_nsg import evaluate_risky_nsg


def run_scan(
    db: Session,
    subscription_db_id: int,
) -> Scan:
    subscription = db.get(Subscription, subscription_db_id)

    if subscription is None:
        raise ValueError("Subscription not found")

    scan = Scan(
        subscription_id=subscription.id,
        trigger_source="api",
        status="running",
        started_at=datetime.utcnow(),
    )

    db.add(scan)
    db.commit()
    db.refresh(scan)

    try:
        resources = load_mock_resources()

        policies = list(
            db.scalars(
                select(PolicyRule).where(
                    PolicyRule.enabled.is_(True)
                )
            ).all()
        )
        for policy in policies:
            if policy.rule_type == "required_tag":
                required_tag = "Environment"

                for resource in resources:
                    violation = evaluate_required_tag(
                        resource=resource,
                        required_tag=required_tag,
                    )

                    if violation is None:
                        continue

                    db.add(
                        Finding(
                            scan_id=scan.id,
                            policy_rule_id=policy.id,
                            resource_id=violation.resource_id,
                            resource_name=violation.resource_name,
                            resource_type=violation.resource_type,
                            severity=policy.severity,
                            status="open",
                            message=violation.message,
                        )
                    )

            elif policy.rule_type == "risky_nsg":
                for resource in resources:
                    violations = evaluate_risky_nsg(resource)

                    for violation in violations:
                        db.add(
                            Finding(
                                scan_id=scan.id,
                                policy_rule_id=policy.id,
                                resource_id=violation.resource_id,
                                resource_name=violation.resource_name,
                                resource_type=violation.resource_type,
                                severity=policy.severity,
                                status="open",
                                message=violation.message,
                            )
                        )

        scan.status = "completed"
        scan.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(scan)

        return scan

    except Exception:
        db.rollback()

        # Reload because rollback expires/reverts pending session state.
        scan = db.get(Scan, scan.id)

        if scan is not None:
            scan.status = "failed"
            scan.completed_at = datetime.utcnow()
            db.commit()

        raise