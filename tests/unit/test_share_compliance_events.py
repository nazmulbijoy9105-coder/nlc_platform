from datetime import date, timedelta

from app.rule_engine.engine import (
    CompanyProfile,
    NLCRuleEngine,
    RuleState,
    ShareComplianceEvent,
)


TODAY = date(2026, 11, 8)


def _event(event_type, event_date, **overrides):
    values = dict(
        event_id=f"{event_type}-event-1",
        event_type=event_type,
        event_date=event_date,
        event_verified=True,
        event_evidence_ref="RJSC_OR_COMPANY_RECORD:verified-event",
        event_verified_at=TODAY,
        event_verified_by="reviewer-uuid",
    )
    values.update(overrides)
    return ShareComplianceEvent(**values)


def _profile(events):
    return CompanyProfile(
        company_id="share-event-test",
        company_name="Share Event Test Ltd",
        incorporation_date=date(2020, 1, 1),
        share_compliance_events=events,
    )


def _flags(events):
    return NLCRuleEngine().evaluate(_profile(events), today=TODAY).flags


def test_missing_or_unverified_allotment_record_does_not_trigger_sh001():
    event = _event(
        "ALLOTMENT",
        TODAY - timedelta(days=100),
        event_verified=False,
        filing_form="XV",
        filing_status=False,
        filing_status_verified=True,
        filing_evidence_ref="RJSC-SEARCH-001",
        filing_verified_at=TODAY,
        filing_verified_by="reviewer-uuid",
    )
    assert "SH-001" not in {flag.rule_id for flag in _flags([event])}


def test_sh001_requires_verified_allotment_and_verified_form_xv_absence():
    event = _event(
        "ALLOTMENT",
        TODAY - timedelta(days=61),
        filing_form="XV",
        filing_status=False,
        filing_status_verified=True,
        filing_evidence_ref="RJSC-SEARCH-002",
        filing_verified_at=TODAY,
        filing_verified_by="reviewer-uuid",
    )
    flags = [flag for flag in _flags([event]) if flag.rule_id == "SH-001"]
    assert len(flags) == 1
    assert flags[0].state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flags[0].eval_state == "UNKNOWN"
    assert flags[0].score_impact == 0


def test_sh002_uses_transfer_registration_date_not_transfer_execution_date():
    event = _event(
        "TRANSFER_REGISTRATION",
        TODAY - timedelta(days=91),
        certificate_issued=False,
        certificate_status_verified=True,
        certificate_evidence_ref="CERTIFICATE-REGISTER-001",
        certificate_verified_at=TODAY,
        certificate_verified_by="reviewer-uuid",
    )
    flags = [flag for flag in _flags([event]) if flag.rule_id == "SH-002"]
    assert len(flags) == 1
    assert flags[0].detail["trigger_type"] == "TRANSFER_REGISTRATION"
    assert flags[0].detail["trigger_date"] == event.event_date.isoformat()
    assert flags[0].score_impact == 0


def test_sh002_applies_to_allotment_certificate_trigger_too():
    event = _event(
        "ALLOTMENT",
        TODAY - timedelta(days=91),
        certificate_issued=False,
        certificate_status_verified=True,
        certificate_evidence_ref="CERTIFICATE-REGISTER-002",
        certificate_verified_at=TODAY,
        certificate_verified_by="reviewer-uuid",
    )
    assert "SH-002" in {flag.rule_id for flag in _flags([event])}


def test_sh003_requires_verified_capital_increase_and_form_iv_status():
    event = _event(
        "CAPITAL_INCREASE",
        TODAY - timedelta(days=16),
        filing_form="IV",
        filing_status=False,
        filing_status_verified=True,
        filing_evidence_ref="RJSC-SEARCH-003",
        filing_verified_at=TODAY,
        filing_verified_by="reviewer-uuid",
    )
    flags = [flag for flag in _flags([event]) if flag.rule_id == "SH-003"]
    assert len(flags) == 1
    assert flags[0].state == RuleState.REQUIRES_LAWYER_JUDGMENT
    assert flags[0].score_impact == 0


def test_unverified_filing_or_certificate_status_is_unknown_not_noncompliant():
    allotment = _event(
        "ALLOTMENT",
        TODAY - timedelta(days=120),
        filing_form="XV",
        filing_status=False,
        filing_status_verified=False,
        filing_evidence_ref=None,
        certificate_issued=False,
        certificate_status_verified=False,
        certificate_evidence_ref=None,
    )
    capital = _event(
        "CAPITAL_INCREASE",
        TODAY - timedelta(days=30),
        filing_form="IV",
        filing_status=False,
        filing_status_verified=False,
        filing_evidence_ref=None,
    )
    assert not {flag.rule_id for flag in _flags([allotment, capital])} & {
        "SH-001", "SH-002", "SH-003"
    }


def test_wrong_filing_form_does_not_trigger_another_share_rule():
    event = _event(
        "ALLOTMENT",
        TODAY - timedelta(days=120),
        filing_form="IV",
        filing_status=False,
        filing_status_verified=True,
        filing_evidence_ref="RJSC-SEARCH-004",
        filing_verified_at=TODAY,
        filing_verified_by="reviewer-uuid",
    )
    assert "SH-001" not in {flag.rule_id for flag in _flags([event])}
