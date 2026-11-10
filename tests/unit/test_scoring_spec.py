"""Tests for the single versioned customer-facing scoring specification."""

from canonical_architecture.scoring_spec import (
    CATEGORY_CAPS,
    CATEGORY_ORDER,
    SCORING_BASE,
    SCORING_SPEC_VERSION,
    allocate_flag_deductions,
    category_deductions_from_flags,
    score_from_category_deductions,
)


def test_category_caps_are_one_ordered_spec_and_keep_legacy_nominal_capacity():
    assert tuple(CATEGORY_CAPS) == CATEGORY_ORDER
    assert sum(cap for cap, _ in CATEGORY_CAPS.values()) == 240
    assert SCORING_BASE == 100
    assert SCORING_SPEC_VERSION


def test_global_100_point_budget_reconciles_applied_components():
    findings = [
        ("TAX-001", 15),
        ("AGM-001", 30),
        ("AUD-001", 25),
        ("AR-002", 20),
        ("DIR-001", 25),
        ("SH-001", 20),
        ("CAP-001", 15),
        ("OFF-001", 10),
        ("REG-001", 10),
        ("BNK-001", 20),
        ("LBR-001", 10),
        ("BSEC-001", 15),
        ("FX-001", 10),
        ("ESC-001", 15),
    ]
    applied = allocate_flag_deductions(findings)
    categories = category_deductions_from_flags(findings)
    final_score = score_from_category_deductions(categories)

    assert sum(applied) == 100
    assert sum(categories.values()) == 100
    assert final_score == 0
    assert 100 - sum(categories.values()) == final_score


def test_category_caps_apply_before_global_budget_and_in_stable_order():
    findings = [
        ("AGM-001", 25),
        ("AGM-002", 25),
        ("AUD-001", 25),
        ("AUD-002", 25),
    ]
    applied = allocate_flag_deductions(findings)
    categories = category_deductions_from_flags(findings)

    assert applied == [25, 5, 25, 25]
    assert categories["AGM"] == 30
    assert categories["AUD"] == 25
    assert sum(applied) == 80


def test_unknown_category_never_receives_an_applied_deduction():
    findings = [("UNKNOWN-001", 100), ("AGM-001", 10)]
    assert allocate_flag_deductions(findings) == [0, 10]
    assert score_from_category_deductions(
        category_deductions_from_flags(findings)
    ) == 90
