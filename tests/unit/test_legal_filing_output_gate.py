from datetime import date, datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

import app.api.filings as filings_api


def _agm():
    return SimpleNamespace(
        id=uuid4(),
        company_id=uuid4(),
        financial_year=2026,
        agm_deadline=date(2026, 6, 30),
        agm_date=None,
        rjsc_filing_date=None,
        quorum_met=True,
        quorum_required=2,
        quorum_basis="ARTICLES",
        venue=None,
        members_present=2,
        members_present_verified=False,
        members_present_evidence_ref=None,
        members_present_verified_at=None,
        members_present_verified_by=None,
        quorum_required_verified=False,
        quorum_evidence_ref=None,
        quorum_verified_at=None,
        quorum_verified_by=None,
        auditor_reappointed=True,
        auditor_reappointment_verified=False,
        auditor_reappointment_evidence_ref=None,
        auditor_reappointment_verified_at=None,
        auditor_reappointment_verified_by=None,
        accounts_adopted=True,
        agm_held_without_audit=False,
        minutes_prepared=True,
        is_default=True,
        created_at=datetime.now(timezone.utc),
    )


def _annual_return():
    return SimpleNamespace(
        id=uuid4(),
        company_id=uuid4(),
        financial_year=2026,
        filed_date=date(2026, 7, 15),
        filing_deadline=date(2026, 8, 14),
        is_default=True,
        rjsc_receipt_number="RJSC-RECEIPT-UNVERIFIED",
        late_fee_paid_bdt=None,
        created_at=datetime.now(timezone.utc),
    )


def test_agm_serializer_hides_unreleased_deadline_and_default(monkeypatch):
    monkeypatch.setattr(filings_api, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(filings_api, "LEGAL_CALENDAR_RELEASED", False)

    response = filings_api._agm_to_response(_agm())

    assert response.agm_due_date is None
    assert response.is_default is None
    assert response.quorum_met is None


def test_annual_return_serializer_hides_unreleased_deadline_and_default(monkeypatch):
    monkeypatch.setattr(filings_api, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(filings_api, "LEGAL_CALENDAR_RELEASED", False)

    response = filings_api._return_to_response(_annual_return())

    assert response.filing_deadline is None
    assert response.is_default is None
    assert response.filing_evidence_status == "RECEIPT_REFERENCE_RECORDED_UNVERIFIED"
