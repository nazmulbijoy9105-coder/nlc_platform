import pytest
from fastapi import HTTPException

from app.services.company_fact_service import CompanyFactService


def test_company_fact_key_must_be_a_supported_profile_field() -> None:
    assert CompanyFactService._normalize_fact_key("registered_office_change_date") == "registered_office_change_date"


def test_company_identity_fields_cannot_be_overridden_by_company_facts() -> None:
    with pytest.raises(HTTPException) as exc:
        CompanyFactService._normalize_fact_key("company_id")
    assert exc.value.status_code == 422
