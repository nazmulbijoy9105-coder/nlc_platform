"""Audit-readiness and FX profile facts must not be overstated as breaches."""

from datetime import date

from app.rule_engine.engine import (
    CompanyProfile,
    NLCRuleEngine,
    RuleState,
    Severity,
)


def _evaluate(**overrides):
    profile = CompanyProfile(
        company_id="audit-fx-evidence-test",
        company_name="Audit FX Evidence Test Ltd",
        incorporation_date=date(2020, 1, 15),
        **overrides,
    )
    return NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)


def _one_flag(output, rule_id: str):
    matches = [flag for flag in output.flags if flag.rule_id == rule_id]
    assert len(matches) == 1
    return matches[0]


def test_aud002_pre_agm_readiness_is_not_a_statutory_default():
    output = _evaluate(
        agm_scheduled_date=date(2026, 11, 20),
        audit_complete=False,
        audit_completion_verified=True,
        audit_completion_evidence_ref="AUDIT-STATUS-001",
        audit_completion_verified_at=date(2026, 11, 14),
        audit_completion_verified_by="reviewer-1",
    )
    finding = _one_flag(output, "AUD-002")
    assert finding.flag_code == "AUDIT_READINESS_REQUIRES_REVIEW"
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.state is RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
    assert finding.detail["statutory_default_established"] is False


def test_aud003_incomplete_audit_at_agm_remains_lawyer_review_not_red_finding():
    output = _evaluate(
        agm_held_this_cycle=True,
        audit_complete=False,
        audit_completion_verified=True,
        audit_completion_evidence_ref="AUDIT-STATUS-002",
        audit_completion_verified_at=date(2026, 11, 14),
        audit_completion_verified_by="reviewer-1",
    )
    finding = _one_flag(output, "AUD-003")
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0


def test_fx_profile_boolean_does_not_establish_a_foreign_exchange_violation():
    output = _evaluate(foreign_exchange_violation=True)
    finding = _one_flag(output, "FX-001")
    assert finding.flag_code == "FOREIGN_EXCHANGE_TRANSACTION_REQUIRES_LEGAL_REVIEW"
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.state is RuleState.REQUIRES_LAWYER_JUDGMENT
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
    assert "UNDERLYING_TRANSACTION_DOCUMENTS" in finding.detail["required_evidence"]
