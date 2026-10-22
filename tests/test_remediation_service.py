from cloudguard.services.remediation_service import requires_approval


def test_medium_finding_does_not_require_approval() -> None:
    assert requires_approval("medium") is False


def test_high_finding_requires_approval() -> None:
    assert requires_approval("high") is True


def test_critical_finding_requires_approval() -> None:
    assert requires_approval("critical") is True


def test_severity_check_is_case_insensitive() -> None:
    assert requires_approval("HIGH") is True