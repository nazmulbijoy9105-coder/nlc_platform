"""Regression tests: annual-return backlog is not automatic strike-off proof."""
from datetime import date

import pytest

from app.rule_engine.engine import RuleState, Severity


pytestmark = [pytest.mark.unit, pytest.mark.rule]


def _rule_flags(output, rule_ids):
    return [flag for flag in output.flags if flag.rule_id in rule_ids]


def test_two_year_return_backlog_is_review_only(rule_engine, build_profile):
    output = rule_engine.evaluate(build_profile(unfiled_returns_count=2))
    flags = _rule_flags(output, {"AR-002"})

    assert len(flags) == 1
    flag = flags[0]
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.is_black_override is False
    assert "Section 346" in flag.statutory_basis


def test_three_year_return_backlog_cannot_create_black_or_strikeoff_finding(
    rule_engine, build_profile
):
    output = rule_engine.evaluate(build_profile(unfiled_returns_count=3))
    flags = _rule_flags(output, {"AR-002", "AR-003"})

    assert {flag.rule_id for flag in flags} == {"AR-002", "AR-003"}
    for flag in flags:
        assert flag.severity == Severity.NOT_EVALUATED
        assert flag.score_impact == 0
        assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
        assert flag.eval_state == "UNKNOWN"
        assert flag.is_black_override is False


def test_reported_rjsc_notice_creates_review_prompt_not_strikeoff_conclusion(
    rule_engine, build_profile
):
    output = rule_engine.evaluate(
        build_profile(
            unfiled_returns_count=0,
            rjsc_strike_off_notice_date=date(2026, 11, 1),
            on_rjsc_strike_off_list=False,
        )
    )
    flags = _rule_flags(output, {"ESC-002"})

    assert len(flags) == 1
    flag = flags[0]
    assert flag.severity == Severity.NOT_EVALUATED
    assert flag.score_impact == 0
    assert flag.state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flag.eval_state == "UNKNOWN"
    assert flag.is_black_override is False
    assert "Section 346" in flag.statutory_basis
