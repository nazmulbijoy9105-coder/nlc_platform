from datetime import date

from app.services.filing_service import AGMService


def test_first_agm_deadline_uses_calendar_months():
    assert AGMService.calculate_first_agm_deadline(date(2024, 1, 31)) == date(2025, 7, 31)
    assert AGMService.calculate_first_agm_deadline(date(2023, 8, 31)) == date(2025, 2, 28)


def test_subsequent_agm_deadline_enforces_fifteen_calendar_month_cap():
    # Incorporation 1 Jan 2020; first AGM 1 Jan 2021. A second AGM is due
    # no later than 1 Apr 2022, not 31 Dec 2022.
    assert AGMService.calculate_subsequent_agm_deadline(
        date(2021, 1, 1), date(2021, 12, 31)
    ) == date(2022, 4, 1)


def test_subsequent_agm_deadline_also_respects_calendar_year():
    assert AGMService.calculate_subsequent_agm_deadline(
        date(2025, 10, 1), date(2025, 12, 31)
    ) == date(2026, 12, 31)
