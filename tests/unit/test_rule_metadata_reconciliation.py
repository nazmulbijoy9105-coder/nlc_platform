"""Require a complete, explicit disposition for every production metadata mismatch."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MISMATCHES = ROOT / "docs" / "release" / "production_rule_metadata_mismatches_2026-11-12.csv"
DISPOSITIONS = ROOT / "docs" / "release" / "rule_metadata_reconciliation_dispositions_2026-11-13.csv"
ALLOWED = {"KEEP_SEED", "KEEP_DATABASE", "REWRITE_WITH_SOURCE", "REQUIRES_PRODUCT_OWNER_DECISION"}


def _rows(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_every_production_metadata_difference_has_exactly_one_disposition():
    mismatches = _rows(MISMATCHES)
    decisions = _rows(DISPOSITIONS)
    mismatch_keys = [(r["rule_id"], r["field"]) for r in mismatches]
    decision_keys = [(r["rule_id"], r["field"]) for r in decisions]

    assert len(mismatch_keys) == 270
    assert len(set(mismatch_keys)) == len(mismatch_keys)
    assert len(decision_keys) == len(mismatch_keys)
    assert len(set(decision_keys)) == len(decision_keys)
    assert set(decision_keys) == set(mismatch_keys)


def test_all_dispositions_are_explicit_and_have_rationales():
    decisions = _rows(DISPOSITIONS)
    assert all(row["disposition"] in ALLOWED for row in decisions)
    assert all(row["rationale"].strip() for row in decisions)
    assert all(row["blocking_condition"].strip() for row in decisions)
    assert all(row["source_reference"].strip() for row in decisions)


def test_historical_inc002_is_not_reactivated_by_reconciliation():
    decisions = _rows(DISPOSITIONS)
    legacy = [row for row in decisions if row["rule_id"] == "INC-002"]
    assert len(legacy) == 1
    assert legacy[0]["field"] == "seed_definition"
    assert legacy[0]["disposition"] == "KEEP_DATABASE"
    assert "inactive" in legacy[0]["rationale"].lower()


def test_legal_citations_are_never_auto_selected():
    decisions = _rows(DISPOSITIONS)
    citation_rows = [row for row in decisions if row["field"] == "statutory_basis"]
    assert citation_rows
    assert all(row["disposition"] == "REWRITE_WITH_SOURCE" for row in citation_rows)
    assert all(not row["preferred_value"].strip() for row in citation_rows)


def test_evaluator_conditions_require_explicit_behavioral_decision():
    decisions = _rows(DISPOSITIONS)
    condition_rows = [row for row in decisions if row["field"] == "rule_condition"]
    assert condition_rows
    assert all(row["disposition"] == "REQUIRES_PRODUCT_OWNER_DECISION" for row in condition_rows)
    assert all(not row["preferred_value"].strip() for row in condition_rows)
