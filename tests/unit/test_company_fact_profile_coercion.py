from datetime import date

import pytest

from app.rule_engine import CompanyProfile
from app.services.compliance_service import _coerce_company_fact_value


def test_date_fact_json_string_is_coerced_to_profile_date() -> None:
    value = _coerce_company_fact_value(
        "registered_office_change_date",
        "2026-11-01",
        CompanyProfile,
    )
    assert value == date(2026, 11, 1)


def test_invalid_date_fact_is_rejected_before_rule_evaluation() -> None:
    with pytest.raises(ValueError, match="ISO date"):
        _coerce_company_fact_value(
            "registered_office_change_date",
            "not-a-date",
            CompanyProfile,
        )
