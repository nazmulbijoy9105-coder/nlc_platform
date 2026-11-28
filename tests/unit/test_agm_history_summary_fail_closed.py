from datetime import datetime, date
from types import SimpleNamespace

from app.services.company_service import _agm_history_summary


def _agm(*, financial_year: int, agm_type: str = "ANNUAL", agm_date: date | None = date(2025, 6, 30)):
    return SimpleNamespace(
        financial_year=financial_year,
        agm_type=agm_type,
        agm_held=True,
        agm_held_verified=True,
        agm_held_evidence_ref=f"agm:{financial_year}:{agm_type}",
        agm_held_verified_at=datetime(2026, 11, 27),
        agm_held_verified_by="independent-reviewer",
        agm_date=agm_date,
    )


def test_duplicate_annual_rows_for_same_financial_year_withhold_history():
    result = _agm_history_summary(
        [_agm(financial_year=2024), _agm(financial_year=2024, agm_date=date(2025, 7, 1))],
        history_marker_verified=True,
    )

    assert result["agm_history_verified"] is False
    assert result["agm_count"] is None
    assert result["last_agm_date"] is None


def test_unknown_agm_type_withholds_history_instead_of_disappearing():
    result = _agm_history_summary(
        [_agm(financial_year=2024), _agm(financial_year=2025, agm_type="SPECIAL")],
        history_marker_verified=True,
    )

    assert result["agm_history_verified"] is False
    assert result["agm_count"] is None
    assert result["last_agm_date"] is None


def test_extraordinary_meeting_is_excluded_without_invalidating_annual_history():
    result = _agm_history_summary(
        [
            _agm(financial_year=2024),
            _agm(financial_year=2024, agm_type="EXTRAORDINARY"),
        ],
        history_marker_verified=True,
    )

    assert result["agm_history_verified"] is True
    assert result["agm_count"] == 1
    assert result["last_agm_date"] == date(2025, 6, 30)
