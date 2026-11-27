from datetime import date, datetime, timezone
from types import SimpleNamespace

from app.rule_engine.engine import CompanyProfile, NLCRuleEngine, RuleState, Severity
from app.services.company_service import _agm_history_summary


def _agm_row(
    agm_date: date,
    *,
    agm_type: str = "ANNUAL",
    held: bool = True,
    verified: bool = True,
    evidence_ref: str | None = "agm-minutes:verified",
):
    return SimpleNamespace(
        agm_date=agm_date,
        agm_type=agm_type,
        agm_held=held,
        agm_held_verified=verified,
        agm_held_evidence_ref=evidence_ref,
        agm_held_verified_at=datetime(2026, 11, 27, tzinfo=timezone.utc)
        if verified else None,
        agm_held_verified_by="reviewer-01" if verified else None,
        is_active=True,
    )


def test_first_agm_provenance_uses_earliest_verified_annual_agm():
    first = _agm_row(date(2024, 10, 1), agm_type="FIRST")
    later = _agm_row(date(2025, 9, 30))
    extraordinary = _agm_row(date(2024, 7, 1), agm_type="EXTRAORDINARY")

    result = _agm_history_summary([later, extraordinary, first], True)

    assert result["agm_history_verified"] is True
    assert result["agm_count"] == 2
    assert result["first_agm_date"] == date(2024, 10, 1)
    assert result["first_agm_date_verified"] is True
    assert result["first_agm_date_evidence_ref"] == "agm-minutes:verified"
    assert result["first_agm_date_verified_by"] == "reviewer-01"
    assert result["last_agm_date"] == date(2025, 9, 30)


def test_first_agm_provenance_fails_closed_when_any_annual_cycle_is_unverified():
    first = _agm_row(date(2024, 10, 1), agm_type="FIRST")
    incomplete = _agm_row(
        date(2025, 9, 30), verified=False, evidence_ref=None
    )

    result = _agm_history_summary([first, incomplete], True)

    assert result["agm_history_verified"] is False
    assert result["agm_count"] is None
    assert result["first_agm_date"] is None
    assert result["first_agm_date_verified"] is False
    assert result["first_agm_date_evidence_ref"] is None


def test_first_agm_date_requires_source_reviewer_and_verification_time():
    profile = CompanyProfile(
        company_id="test-company",
        company_name="Test Company Ltd",
        incorporation_date=date(2023, 1, 1),
        agm_count=1,
        agm_history_verified=True,
        last_agm_date=date(2024, 10, 1),
        first_agm_date=date(2024, 10, 1),
        first_agm_date_verified=True,
        first_agm_date_evidence_ref="agm-minutes:verified",
        first_agm_date_verified_at=date(2026, 11, 27),
        first_agm_date_verified_by="reviewer-01",
    )
    engine = NLCRuleEngine()

    assert engine._first_agm_date_is_verified(profile) is True
    assert engine._subsequent_agm_deadline_components(profile) is not None

    profile.first_agm_date_evidence_ref = None
    assert engine._first_agm_date_is_verified(profile) is False
    assert engine._subsequent_agm_deadline_components(profile) is None


def test_first_agm_event_does_not_reopen_agm001_after_verified_holding():
    profile = CompanyProfile(
        company_id="test-company",
        company_name="Test Company Ltd",
        incorporation_date=date(2023, 1, 1),
        agm_count=1,
        agm_history_verified=True,
        agm_history_evidence_ref="agm-history:verified",
        agm_history_verified_at=date(2026, 11, 27),
        agm_history_verified_by="reviewer-01",
        last_agm_date=date(2024, 10, 1),
        first_agm_date=date(2024, 10, 1),
        first_agm_date_verified=True,
        first_agm_date_evidence_ref="agm-minutes:verified",
        first_agm_date_verified_at=date(2026, 11, 27),
        first_agm_date_verified_by="reviewer-01",
    )
    engine = NLCRuleEngine()
    engine.evaluate(profile, today=date(2026, 11, 27))

    assert not any(flag.rule_id == "AGM-001" for flag in engine._flags)
