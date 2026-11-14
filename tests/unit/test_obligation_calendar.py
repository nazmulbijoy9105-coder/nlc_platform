from datetime import date

from app.services.obligation_calendar import (
    Applicability,
    DueKind,
    add_calendar_months,
    build_private_company_calendar,
)


def _items(**overrides):
    args = {
        "as_of": date(2026, 11, 15),
        "company_type": "PRIVATE_LIMITED",
        "company_type_verified": True,
        "incorporation_date": date(2024, 1, 31),
        "agm_dates": [date(2025, 6, 30)],
        "agm_history_verified": True,
        "board_meeting_dates": [date(2026, 8, 15)],
        "board_history_verified": True,
        "financial_year_start": date(2026, 7, 1),
        "financial_year_end": date(2027, 6, 30),
        "first_auditor_appointed": None,
        "first_auditor_status_verified": False,
        "bsec_listed": None,
        "bsec_listing_verified": False,
        "is_subsidiary_of_listed_issuer": None,
        "subsidiary_scope_verified": False,
    }
    args.update(overrides)
    return build_private_company_calendar(**args)


def test_calendar_month_arithmetic_clamps_month_end():
    assert add_calendar_months(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert add_calendar_months(date(2025, 1, 31), 1) == date(2025, 2, 28)


def test_private_company_calendar_has_agm_financials_audit_and_board_cycles():
    items = {item.obligation_id: item for item in _items()}
    assert items["AGM-81"].due_date == date(2026, 12, 31)
    assert items["ACC-183"].due_date == items["AGM-81"].due_date
    assert items["AUD-210-AGM"].due_date == items["AGM-81"].due_date
    assert items["BOD-96"].due_date == date(2026, 11, 15)
    assert items["BOD-96"].due_kind == DueKind.STATUTORY_DEADLINE
    assert not any(key.startswith("BSEC-AC-") for key in items)


def test_unverified_agm_and_board_history_never_fabricate_due_dates():
    items = {item.obligation_id: item for item in _items(
        agm_history_verified=False,
        board_history_verified=False,
    )}
    assert items["AGM-81"].due_date is None
    assert items["AGM-81"].applicability == Applicability.APPLICABLE
    assert items["BOD-96"].due_date is None


def test_private_subsidiary_listing_scope_stays_unknown_until_verified():
    items = {item.obligation_id: item for item in _items()}
    assert items["BSEC-SCOPE"].applicability == Applicability.UNKNOWN


def test_verified_unlisted_private_company_has_no_bsec_code_calendar():
    items = _items(
        bsec_listed=False,
        bsec_listing_verified=True,
        is_subsidiary_of_listed_issuer=False,
        subsidiary_scope_verified=True,
    )
    assert not any(item.obligation_id.startswith("BSEC-") for item in items)


def test_listed_issuer_gets_four_audit_committee_planning_targets_and_review_windows():
    items = _items(
        company_type="PUBLIC_LIMITED",
        bsec_listed=True,
        bsec_listing_verified=True,
    )
    committee = [item for item in items if item.obligation_id.startswith("BSEC-AC-5(4)-Q")]
    assert len(committee) == 4
    assert all(item.due_kind == DueKind.INTERNAL_PLANNING_TARGET for item in committee)
    assert any(item.obligation_id == "BSEC-AC-5(5)(g)-Q" for item in items)
    assert any(item.obligation_id == "BSEC-AC-5(5)(g)-H" for item in items)
