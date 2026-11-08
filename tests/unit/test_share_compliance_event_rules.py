from __future__ import annotations

from datetime import date, timedelta

from app.rule_engine.engine import ShareComplianceEventEvidence
from tests.conftest import assert_flag_not_triggered, assert_flag_triggered


def _event(
    event_type: str,
    event_date: date,
    *,
    reference: str,
    filing_form: str | None = None,
    filing_status: bool | None = None,
    filing_verified: bool = False,
    certificate_issued: bool | None = None,
    certificate_verified: bool = False,
) -> ShareComplianceEventEvidence:
    return ShareComplianceEventEvidence(
        event_reference=reference,
        event_type=event_type,
        event_date=event_date,
        event_verified=True,
        event_evidence_ref=f"hardcopy://{reference}",
        filing_form=filing_form,
        filing_status=filing_status,
        filing_status_verified=filing_verified,
        filing_evidence_ref=f"rjsc://{reference}/filing" if filing_verified else None,
        certificate_issued=certificate_issued,
        certificate_status_verified=certificate_verified,
        certificate_evidence_ref=(
            f"register://{reference}/certificate" if certificate_verified else None
        ),
    )


def test_sh001_uses_verified_allotment_and_form_xv_trigger(rule_engine, build_profile):
    today = date(2026, 11, 8)
    event = _event(
        "ALLOTMENT", today - timedelta(days=61), reference="ALLOT-2026-01",
        filing_form="FORM_XV", filing_status=False, filing_verified=True,
    )
    output = rule_engine.evaluate(
        build_profile(
            share_compliance_events=[event],
            last_allotment_date=None,
            form_xv_filed=None,
        ),
        today=today,
    )
    assert_flag_triggered(output, "SH-001")
    flag = next(item for item in output.flags if item.rule_id == "SH-001")
    assert flag.detail["event_reference"] == "ALLOT-2026-01"
    assert flag.detail["delay_days"] == 61


def test_sh001_does_not_fail_at_day_60_or_on_unverified_filing(rule_engine, build_profile):
    today = date(2026, 11, 8)
    on_deadline = _event(
        "ALLOTMENT", today - timedelta(days=60), reference="ALLOT-ON-TIME",
        filing_form="FORM_XV", filing_status=False, filing_verified=True,
    )
    unknown = _event(
        "ALLOTMENT", today - timedelta(days=90), reference="ALLOT-UNKNOWN",
        filing_form="FORM_XV", filing_status=False, filing_verified=False,
    )
    output = rule_engine.evaluate(
        build_profile(share_compliance_events=[on_deadline, unknown]),
        today=today,
    )
    assert_flag_not_triggered(output, "SH-001")


def test_sh002_uses_transfer_registration_date_under_section_158(rule_engine, build_profile):
    today = date(2026, 11, 8)
    event = _event(
        "TRANSFER_REGISTERED", today - timedelta(days=91), reference="TRANSFER-REG-01",
        certificate_issued=False, certificate_verified=True,
    )
    output = rule_engine.evaluate(
        build_profile(share_compliance_events=[event], last_allotment_date=None),
        today=today,
    )
    assert_flag_triggered(output, "SH-002")
    flag = next(item for item in output.flags if item.rule_id == "SH-002")
    assert flag.detail["event_type"] == "TRANSFER_REGISTERED"
    assert flag.detail["event_reference"] == "TRANSFER-REG-01"


def test_sh003_uses_capital_increase_resolution_date_and_form_iv(rule_engine, build_profile):
    today = date(2026, 11, 8)
    event = _event(
        "CAPITAL_INCREASE_RESOLUTION", today - timedelta(days=16), reference="SR-2026-04",
        filing_form="FORM_IV", filing_status=False, filing_verified=True,
    )
    output = rule_engine.evaluate(
        build_profile(
            share_compliance_events=[event],
            capital_increase_date=None,
            form_iv_filed=None,
        ),
        today=today,
    )
    assert_flag_triggered(output, "SH-003")
    flag = next(item for item in output.flags if item.rule_id == "SH-003")
    assert flag.detail["event_reference"] == "SR-2026-04"
    assert flag.detail["delay_days"] == 16


def test_unverified_event_never_becomes_a_share_breach(rule_engine, build_profile):
    today = date(2026, 11, 8)
    event = ShareComplianceEventEvidence(
        event_reference="ALLOT-UNVERIFIED",
        event_type="ALLOTMENT",
        event_date=today - timedelta(days=200),
        event_verified=False,
        event_evidence_ref=None,
        filing_form="FORM_XV",
        filing_status=False,
        filing_status_verified=True,
    )
    output = rule_engine.evaluate(build_profile(share_compliance_events=[event]), today=today)
    assert_flag_not_triggered(output, "SH-001")
