from datetime import date

from app.rule_engine.engine import (
    CompanyProfile,
    NLCRuleEngine,
    RuleState,
    Severity,
)


def _profile(**overrides):
    values = {
        "company_id": "RULE-BIND-1",
        "company_name": "Rule Binding Test Ltd",
        "company_type": "PRIVATE_LIMITED",
        "incorporation_date": date(2020, 1, 1),
        "catalogue_binding_required": True,
        "catalogue_rule_versions": {"BOD-001": "3.4"},
        "catalogue_rule_active": {"BOD-001": True},
        "catalogue_rule_bases": {"BOD-001": "Section 96, Companies Act 1994 (Bangladesh)"},
    }
    values.update(overrides)
    return CompanyProfile(**values)


def test_engine_finding_uses_database_rule_version_not_engine_version():
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(_profile())
    finding = next(flag for flag in output.flags if flag.rule_id == "BOD-001")
    assert finding.rule_version == "3.4"
    assert finding.detail.get("rule_catalogue_binding") is None


def test_inactive_catalogue_rule_is_suppressed_fail_closed():
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(
        _profile(catalogue_rule_active={"BOD-001": False})
    )
    finding = next(flag for flag in output.flags if flag.rule_id == "BOD-001")
    assert finding.detail["rule_catalogue_binding"] == "RULE_INACTIVE"
    assert finding.severity == Severity.NOT_EVALUATED
    assert finding.state == RuleState.UNKNOWN
    assert finding.score_impact == 0
    assert finding.is_black_override is False


def test_missing_catalogue_entry_is_suppressed_fail_closed():
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(
        _profile(catalogue_rule_versions={}, catalogue_rule_active={})
    )
    finding = next(flag for flag in output.flags if flag.rule_id == "BOD-001")
    assert finding.detail["rule_catalogue_binding"] == "CATALOGUE_ENTRY_MISSING"
    assert finding.severity == Severity.NOT_EVALUATED
    assert finding.state == RuleState.UNKNOWN
    assert finding.score_impact == 0



def test_statutory_basis_mismatch_is_quarantined_even_when_rule_id_is_active():
    output = NLCRuleEngine(today=date(2026, 11, 15)).evaluate(
        _profile(
            catalogue_rule_bases={
                "BOD-001": "Section 9, Companies Act 1994 (Bangladesh)"
            }
        )
    )
    finding = next(flag for flag in output.flags if flag.rule_id == "BOD-001")
    assert finding.detail["rule_catalogue_binding"] == "STATUTORY_BASIS_MISMATCH"
    assert finding.detail["engine_flag_statutory_basis"] == (
        "Section 96, Companies Act 1994 (Bangladesh)"
    )
    assert finding.detail["catalogue_rule_statutory_basis"] == (
        "Section 9, Companies Act 1994 (Bangladesh)"
    )
    assert finding.severity == Severity.NOT_EVALUATED
    assert finding.state == RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.score_impact == 0
    assert finding.is_black_override is False
    assert finding.conditional_applies is False
