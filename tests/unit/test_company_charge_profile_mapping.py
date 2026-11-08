from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from app.services.company_service import _charge_event_from_record


def _charge(**overrides):
    values = {
        "id": uuid4(),
        "creation_date": date(2025, 1, 10),
        "charge_type": "MORTGAGE",
        "amount_bdt": Decimal("100000.00"),
        "charge_holder": "Example Bank",
        "form_xviii_filed": False,
        "form_xviii_filed_date": None,
        "registrable_under_s159": True,
        "satisfied": False,
        "satisfaction_date": None,
        "satisfaction_filed": None,
        "satisfaction_filed_date": None,
        "creation_date_verified": False,
        "creation_date_evidence_ref": None,
        "creation_date_verified_at": None,
        "creation_date_verified_by": None,
        "form_xviii_filing_status_verified": False,
        "form_xviii_filing_evidence_ref": None,
        "form_xviii_verified_at": None,
        "form_xviii_verified_by": None,
        "registrability_verified": False,
        "registrability_evidence_ref": None,
        "registrability_verified_at": None,
        "registrability_verified_by": None,
        "satisfaction_verified": False,
        "satisfaction_evidence_ref": None,
        "satisfaction_verified_at": None,
        "satisfaction_verified_by": None,
        "satisfaction_filing_status_verified": False,
        "satisfaction_filing_evidence_ref": None,
        "satisfaction_filing_verified_at": None,
        "satisfaction_filing_verified_by": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_unverified_reported_charge_facts_are_not_promoted_to_engine():
    event = _charge_event_from_record(_charge())

    assert event.creation_date_verified is False
    assert event.form_xviii_filed is None
    assert event.form_xviii_filed_date is None
    assert event.registrable_under_s159 is None
    assert event.satisfied is None
    assert event.satisfaction_date is None
    assert event.satisfaction_filed is None
    assert event.satisfaction_filed_date is None


def test_charge_facts_require_complete_reviewer_provenance():
    now = datetime(2026, 11, 8, tzinfo=timezone.utc)
    reviewer = uuid4()
    event = _charge_event_from_record(_charge(
        creation_date_verified=True,
        creation_date_evidence_ref="doc://charge-creation",
        creation_date_verified_at=now,
        creation_date_verified_by=reviewer,
        form_xviii_filing_status_verified=True,
        form_xviii_filing_evidence_ref="doc://form-xviii",
        form_xviii_verified_at=now,
        form_xviii_verified_by=reviewer,
        registrability_verified=True,
        registrability_evidence_ref="doc://registrability",
        registrability_verified_at=now,
        registrability_verified_by=reviewer,
        satisfaction_verified=True,
        satisfaction_evidence_ref="doc://satisfaction",
        satisfaction_verified_at=now,
        satisfaction_verified_by=reviewer,
        satisfaction_filing_status_verified=True,
        satisfaction_filing_evidence_ref="doc://form-xxviii",
        satisfaction_filing_verified_at=now,
        satisfaction_filing_verified_by=reviewer,
        form_xviii_filed=True,
        form_xviii_filed_date=date(2025, 1, 20),
        registrable_under_s159=True,
        satisfied=True,
        satisfaction_date=date(2026, 2, 1),
        satisfaction_filed=True,
        satisfaction_filed_date=date(2026, 2, 10),
    ))

    assert event.creation_date_verified is True
    assert event.form_xviii_filed is True
    assert event.form_xviii_filed_date == date(2025, 1, 20)
    assert event.registrable_under_s159 is True
    assert event.satisfied is True
    assert event.satisfaction_date == date(2026, 2, 1)
    assert event.satisfaction_filed is True
    assert event.satisfaction_filed_date == date(2026, 2, 10)


def test_incomplete_verifier_metadata_keeps_reported_status_unknown():
    event = _charge_event_from_record(_charge(
        form_xviii_filed=True,
        form_xviii_filing_status_verified=True,
        form_xviii_filing_evidence_ref="doc://form-xviii",
        # Missing reviewer timestamp and identity: provenance is incomplete.
    ))

    assert event.form_xviii_filing_status_verified is False
    assert event.form_xviii_filed is None
    assert event.form_xviii_filing_evidence_ref is None
