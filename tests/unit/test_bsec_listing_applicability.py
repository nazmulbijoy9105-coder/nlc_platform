from datetime import date

from app.rule_engine.engine import (
    CompanyProfile,
    NLCRuleEngine,
    RuleState,
    Severity,
)


def test_private_company_does_not_receive_bsec_code_findings_when_unlisted():
    profile = CompanyProfile(
        company_id="BSEC-PRIVATE-1",
        company_name="Private Test Ltd",
        company_type="PRIVATE_LIMITED",
        bsec_listed=False,
    )
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    assert not any(flag.rule_id.startswith("BSEC-") for flag in output.flags)


def test_private_company_positive_listing_flag_is_an_unknown_scope_conflict():
    profile = CompanyProfile(
        company_id="BSEC-PRIVATE-2",
        company_name="Private Test Ltd",
        company_type="PRIVATE_LIMITED",
        bsec_listed=True,
    )
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    flags = [flag for flag in output.flags if flag.rule_id.startswith("BSEC-")]
    assert {flag.rule_id for flag in flags} == {
        "BSEC-001", "BSEC-002", "BSEC-003", "BSEC-004"
    }
    assert all(flag.state == RuleState.UNKNOWN for flag in flags)
    assert all(flag.severity == Severity.NOT_EVALUATED for flag in flags)
    assert all(flag.score_impact == 0 for flag in flags)


def test_public_company_unknown_listing_status_stays_unknown():
    profile = CompanyProfile(
        company_id="BSEC-PUBLIC-1",
        company_name="Public Test Ltd",
        company_type="PUBLIC_LIMITED",
        bsec_listed=None,
    )
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)
    flags = [flag for flag in output.flags if flag.rule_id.startswith("BSEC-")]
    assert len(flags) == 4
    assert all(flag.state == RuleState.UNKNOWN for flag in flags)
