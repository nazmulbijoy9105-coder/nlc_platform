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
