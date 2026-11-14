from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.filings import _validate_annual_return_verification


def _annual_return(submitted_by=None):
    return SimpleNamespace(filing_status_submitted_by=submitted_by)


def test_filing_claim_cannot_be_verified_by_same_submitter():
    actor = uuid4()
    with pytest.raises(HTTPException) as exc:
        _validate_annual_return_verification(
            _annual_return(actor),
            actor,
            filed=True,
            filed_date=date(2026, 11, 1),
        )
    assert exc.value.status_code == 409


def test_different_reviewer_can_verify_filed_claim_with_date():
    _validate_annual_return_verification(
        _annual_return(uuid4()),
        uuid4(),
        filed=True,
        filed_date=date(2026, 11, 1),
        today=date(2026, 11, 14),
    )


def test_non_filing_verification_cannot_include_filing_date():
    with pytest.raises(HTTPException) as exc:
        _validate_annual_return_verification(
            _annual_return(),
            uuid4(),
            filed=False,
            filed_date=date(2026, 11, 1),
            today=date(2026, 11, 14),
        )
    assert exc.value.status_code == 422


def test_filed_verification_requires_date():
    with pytest.raises(HTTPException) as exc:
        _validate_annual_return_verification(
            _annual_return(),
            uuid4(),
            filed=True,
            filed_date=None,
        )
    assert exc.value.status_code == 422


def test_future_filing_date_is_rejected():
    with pytest.raises(HTTPException) as exc:
        _validate_annual_return_verification(
            _annual_return(),
            uuid4(),
            filed=True,
            filed_date=date(2026, 11, 15),
            today=date(2026, 11, 14),
        )
    assert exc.value.status_code == 422


def test_annual_return_deadline_is_21_days_after_agm():
    from app.services.filing_service import AnnualReturnService

    assert AnnualReturnService.calculate_filing_deadline(date(2026, 6, 30)) == date(2026, 7, 21)
