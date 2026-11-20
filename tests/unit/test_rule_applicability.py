from datetime import date, datetime, timezone
from types import SimpleNamespace

from canonical_architecture.applicability_model import ApplicabilityRule
from app.compliance.rule_applicability import (
    APPLICABILITY_POLICY_VERSION,
    evaluate_rule_applicability,
)


class _Fact:
    def __init__(self, key, value, *, verified=True, record_id=None):
        self.fact_key = key
        self.value = value
        self.record_id = record_id or f"fact-{key}"
        self.trust_level = "AUTHORIZED_DOCUMENT_BACKED" if verified else "USER_ASSERTED"
        self.verification_status = "VERIFIED" if verified else "UNVERIFIED"
        self.source_reference = f"evidence:{key}" if verified else None
        self.document_id = f"doc-{key}" if verified else None
        self.observed_on = date(2026, 11, 20)
        self.verified_by = "reviewer-1" if verified else None
        self.verified_at = datetime(2026, 11, 20, tzinfo=timezone.utc) if verified else None
        self._verified = verified

    def is_verified_document_fact(self):
        return self._verified


def _policy():
    return {
        "TEST-001": ApplicabilityRule(
            "TEST-001",
            ("ALL",),
            ("is_active", "agm_scheduled"),
            ("statutory_exemption",),
            "Test policy only.",
        )
    }


def test_missing_policy_is_unknown_not_applicable():
    result = evaluate_rule_applicability("NO-POLICY", {}, policy_registry=_policy())
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "NO_EXPLICIT_APPLICABILITY_POLICY"


def test_missing_or_unverified_facts_are_unknown():
    result = evaluate_rule_applicability(
        "TEST-001",
        {"is_active": _Fact("is_active", True, verified=True)},
        policy_registry=_policy(),
    )
    assert result["status"] == "UNKNOWN"
    assert "agm_scheduled" in result["reason"]
    assert "statutory_exemption" in result["reason"]

    unverified = evaluate_rule_applicability(
        "TEST-001",
        {
            "is_active": _Fact("is_active", True, verified=False),
            "agm_scheduled": _Fact("agm_scheduled", True, verified=True),
            "statutory_exemption": _Fact("statutory_exemption", False, verified=True),
        },
        policy_registry=_policy(),
    )
    assert unverified["status"] == "UNKNOWN"
    assert "is_active" in unverified["reason"]


def test_applicable_requires_all_conditions_and_explicit_false_exception():
    result = evaluate_rule_applicability(
        "TEST-001",
        {
            "is_active": _Fact("is_active", True),
            "agm_scheduled": _Fact("agm_scheduled", "2026-12-01"),
            "statutory_exemption": _Fact("statutory_exemption", False),
        },
        policy_registry=_policy(),
    )
    assert result["status"] == "APPLICABLE"
    assert result["policy_version"] == APPLICABILITY_POLICY_VERSION
    assert {item["fact_key"] for item in result["fact_evidence"]} == {
        "is_active", "agm_scheduled", "statutory_exemption"
    }


def test_verified_false_condition_and_true_exception_are_not_applicable():
    false_condition = evaluate_rule_applicability(
        "TEST-001",
        {
            "is_active": _Fact("is_active", False),
            "agm_scheduled": _Fact("agm_scheduled", "2026-12-01"),
            "statutory_exemption": _Fact("statutory_exemption", False),
        },
        policy_registry=_policy(),
    )
    assert false_condition["status"] == "NOT_APPLICABLE"
    assert false_condition["reason"] == "VERIFIED_SCOPE_CONDITION_FALSE:is_active"

    true_exception = evaluate_rule_applicability(
        "TEST-001",
        {
            "is_active": _Fact("is_active", True),
            "agm_scheduled": _Fact("agm_scheduled", "2026-12-01"),
            "statutory_exemption": _Fact("statutory_exemption", True),
        },
        policy_registry=_policy(),
    )
    assert true_exception["status"] == "NOT_APPLICABLE"
    assert true_exception["reason"] == "VERIFIED_EXCEPTION_TRUE:statutory_exemption"


def test_non_boolean_exception_is_unknown_not_assumed_false():
    result = evaluate_rule_applicability(
        "TEST-001",
        {
            "is_active": _Fact("is_active", True),
            "agm_scheduled": _Fact("agm_scheduled", "2026-12-01"),
            "statutory_exemption": _Fact("statutory_exemption", "not reviewed"),
        },
        policy_registry=_policy(),
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "EXCEPTION_FACT_NOT_BOOLEAN:statutory_exemption"


def test_company_type_scope_requires_verified_company_type():
    policy = {
        "TEST-002": ApplicabilityRule(
            "TEST-002", ("PRIVATE_LIMITED",), ("is_active",), (), "Test scope."
        )
    }
    missing_type = evaluate_rule_applicability(
        "TEST-002",
        {"is_active": _Fact("is_active", True)},
        policy_registry=policy,
    )
    assert missing_type["status"] == "UNKNOWN"

    public_company = evaluate_rule_applicability(
        "TEST-002",
        {
            "company_type": _Fact("company_type", "PUBLIC_LIMITED"),
            "is_active": _Fact("is_active", True),
        },
        policy_registry=policy,
    )
    assert public_company["status"] == "NOT_APPLICABLE"
