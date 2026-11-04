from datetime import date

from app.rule_engine.engine import NLCRuleEngine, RuleState, Severity
from tests.unit.test_legal_evidence_scoring_gates import _profile, _flag


def test_paid_up_authorized_capital_mismatch_is_not_automatic_black():
    result = NLCRuleEngine().evaluate(
        _profile(paid_up_capital_bdt=2_000_000, authorized_capital_bdt=1_000_000),
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
        _profile(capital_reduction_pending=True, capital_reduction_court_order_obtained=False),
        today=date(2026, 11, 4),
    )
    flag = _flag(result, "CAP-003")
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.is_black_override is False
