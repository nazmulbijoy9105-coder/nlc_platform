from datetime import date

from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, RuleState, Severity


def _flag(result, rule_id):
    return next(flag for flag in result.flags if flag.rule_id == rule_id)


def test_paid_up_authorized_capital_mismatch_is_not_automatic_black():
    result = NLCRuleEngine().evaluate(
        CompanyProfile(company_id="CAP-TEST-1", company_name="Capital Test Ltd", incorporation_date=date(2020, 1, 1), paid_up_capital_bdt=2_000_000, authorized_capital_bdt=1_000_000),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "INC-004")
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.is_black_override is False


def test_pending_capital_reduction_is_not_automatic_black():
    result = NLCRuleEngine().evaluate(
        CompanyProfile(company_id="CAP-TEST-2", company_name="Reduction Test Ltd", incorporation_date=date(2020, 1, 1), capital_reduction_pending=True, capital_reduction_court_order_obtained=False),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "CAP-003")
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.is_black_override is False
