"""Accounting-rule assertions must not become statutory findings without evidence."""

from datetime import date

from app.rule_engine.engine import (
    CompanyProfile,
    NLCRuleEngine,
    RuleState,
    Severity,
)


def _evaluate(**overrides):
    profile = CompanyProfile(
        company_id="accounting-evidence-test",
        company_name="Accounting Evidence Test Ltd",
        incorporation_date=date(2020, 1, 15),
        **overrides,
    )
    return NLCRuleEngine(today=date(2026, 11, 15)).evaluate(profile)


def _assert_review_only(output, rule_id: str, expected_flag_code: str) -> None:
    matches = [flag for flag in output.flags if flag.rule_id == rule_id]
    assert len(matches) == 1
    finding = matches[0]
    assert finding.flag_code == expected_flag_code
    assert finding.state is RuleState.UNKNOWN
    assert finding.eval_state == "UNKNOWN"
    assert finding.severity is Severity.NOT_EVALUATED
    assert finding.score_impact == 0


def test_acc001_profile_boolean_does_not_prove_financial_statements_omitted():
    output = _evaluate(
        agm_held_this_cycle=True,
        financial_statements_presented=False,
    )
    _assert_review_only(
        output,
        "ACC-001",
        "FINANCIAL_STATEMENTS_PRESENTATION_REQUIRES_VERIFICATION",
    )


def test_acc002_profile_boolean_does_not_prove_rjsc_non_filing():
    output = _evaluate(
        agm_held_this_cycle=True,
        agm_history_verified=True,
        agm_history_evidence_ref="AGM-HISTORY-ASSERTED",
        agm_history_verified_at=date(2026, 11, 1),
        agm_history_verified_by="reviewer-1",
        last_agm_date=date(2026, 3, 31),
        financial_statements_filed=False,
    )
    _assert_review_only(
        output,
        "ACC-002",
        "FINANCIAL_STATEMENTS_FILING_REQUIRES_VERIFICATION",
    )


def test_acc003_profile_boolean_does_not_prove_books_not_kept():
    output = _evaluate(books_of_account_kept=False)
    _assert_review_only(
        output,
        "ACC-003",
        "BOOKS_OF_ACCOUNT_STATUS_REQUIRES_VERIFICATION",
    )
