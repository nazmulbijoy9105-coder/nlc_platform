from types import SimpleNamespace

import pytest

from app.compliance.outcome_status import derive_compliance_outcome


@pytest.mark.parametrize(
    ("state", "evaluation", "verified", "expected"),
    [
        ("COMPLIANT", "PASS", True, "COMPLIANT"),
        ("COMPLIANT", "PASS", False, "REVIEW_REQUIRED"),
        ("NON_COMPLIANT", "VIOLATION", True, "NON_COMPLIANT"),
        ("VERIFIED_ABSENT", "VIOLATION", True, "NON_COMPLIANT"),
        ("UNKNOWN", "UNKNOWN", True, "REVIEW_REQUIRED"),
        ("UNKNOWN", "NOT_EVALUATED", True, "REVIEW_REQUIRED"),
        ("UNKNOWN", "NOT_AUTHORISED", True, "NOT_AUTHORISED"),
        ("UNKNOWN", "FAILED", True, "FAILED"),
        ("UNKNOWN", "NOT_PASS", True, "NOT_PASS"),
        ("NOT_APPLICABLE", "NOT_APPLICABLE", True, "NOT_APPLICABLE"),
    ],
)
def test_outcome_is_fail_closed(state, evaluation, verified, expected):
    flag = SimpleNamespace(
        state=state,
        eval_state=evaluation,
        resolved=False,
        conditional_applies=True,
    )
    assert derive_compliance_outcome(flag, counsel_verified_rule=verified) == expected


def test_active_lifecycle_does_not_make_finding_compliant():
    flag = SimpleNamespace(
        state="UNKNOWN",
        eval_state="NOT_EVALUATED",
        resolved=False,
        conditional_applies=True,
        flag_status="ACTIVE",
    )
    assert derive_compliance_outcome(flag, counsel_verified_rule=True) == "REVIEW_REQUIRED"


def test_resolved_is_not_equivalent_to_compliant():
    flag = SimpleNamespace(
        state="COMPLIANT",
        eval_state="PASS",
        resolved=True,
        conditional_applies=True,
    )
    assert derive_compliance_outcome(flag, counsel_verified_rule=True) == "RESOLVED"


def test_not_applicable_condition_is_not_positive_compliance():
    flag = SimpleNamespace(
        state="COMPLIANT",
        eval_state="PASS",
        resolved=False,
        conditional_applies=False,
    )
    assert derive_compliance_outcome(flag, counsel_verified_rule=True) == "NOT_APPLICABLE"


def test_unknown_applicability_never_becomes_compliant():
    flag = SimpleNamespace(
        state="COMPLIANT", eval_state="PASS", conditional_applies=None,
        resolved=False,
    )
    assert derive_compliance_outcome(flag, counsel_verified_rule=True) == "REVIEW_REQUIRED"
