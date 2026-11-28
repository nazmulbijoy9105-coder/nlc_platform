import pytest
from fastapi import HTTPException

from app.services.company_fact_service import CompanyFactService


def test_scalar_company_profile_fact_key_is_supported() -> None:
    assert CompanyFactService._normalize_fact_key("registered_office_change_date") == "registered_office_change_date"


def test_company_identity_fields_cannot_be_overridden() -> None:
    with pytest.raises(HTTPException) as exc:
        CompanyFactService._normalize_fact_key("company_id")
    assert exc.value.status_code == 422


def test_structured_profile_collections_require_typed_workflow() -> None:
    with pytest.raises(HTTPException) as exc:
        CompanyFactService._normalize_fact_key("director_changes")
    assert exc.value.status_code == 422


def test_agm_court_order_status_requires_thirty_day_refresh() -> None:
    from datetime import date, timedelta

    from app.compliance.fact_provenance import (
        fact_freshness_max_age_days,
        fact_freshness_status,
    )

    today = date(2026, 11, 28)
    assert fact_freshness_max_age_days("agm_court_order_evidence") == 30
    assert fact_freshness_status(
        "agm_court_order_evidence", today - timedelta(days=30), today
    ) == "FRESH"
    assert fact_freshness_status(
        "agm_court_order_evidence", today - timedelta(days=31), today
    ) == "STALE"


def test_agm_structured_facts_are_not_accepted_by_user_asserted_scalar_path() -> None:
    for fact_key in (
        "agm_court_order_evidence",
        "agm_court_order_lawyer_decision",
    ):
        with pytest.raises(HTTPException) as exc:
            CompanyFactService._normalize_fact_key(fact_key)
        assert exc.value.status_code == 422
