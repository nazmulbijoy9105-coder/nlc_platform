from datetime import date

import pytest

from app.compliance.fact_provenance import coerce_company_profile_fact_value


def test_date_fact_json_string_is_coerced_to_profile_date() -> None:
    value = coerce_company_profile_fact_value(
        "registered_office_change_date",
        "2026-11-01",
    )
    assert value == date(2026, 11, 1)


def test_invalid_date_fact_is_rejected_before_rule_evaluation() -> None:
    with pytest.raises(ValueError, match="ISO date"):
        coerce_company_profile_fact_value(
            "registered_office_change_date",
            "not-a-date",
        )


def test_null_is_rejected_for_non_nullable_profile_field() -> None:
    with pytest.raises(ValueError, match="cannot be null"):
        coerce_company_profile_fact_value("company_type", None)
