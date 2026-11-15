"""CI checks that registry drift is documented and exceptions are governed."""
import json
from pathlib import Path


MANIFEST = Path(__file__).resolve().parents[1] / "docs" / "legal_rule_registry" / "registry_86_reconciliation.json"


def test_manifest_covers_exactly_86_rules_and_records_source_fields():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["reconciliation"]["rule_count"] == 86
    assert len(data["rules"]) == 86
    for rule_id, item in data["rules"].items():
        assert item["seed_present"] or item["production_database_present"]
        assert "engine_product_scoring_member" in item
        assert "engine_score_deduction_member" in item
        assert "engine_counsel_verified_member" in item
        assert "seed_fields" in item and "production_database_fields" in item
        assert set(item["differing_fields"]) == set(item["field_reconciliation"])


def test_every_difference_is_documented_or_an_approved_exception():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    approved = {x["id"]: x for x in data.get("approved_exceptions", [])}
    for rule_id, item in data["rules"].items():
        for field, record in item["field_reconciliation"].items():
            assert record["status"] in {"DOCUMENTED_UNRESOLVED", "APPROVED_EXCEPTION"}
            if record["status"] == "APPROVED_EXCEPTION":
                exception = approved[record["exception_id"]]
                for required in ("reviewer", "approval_reference", "approved_at", "rationale", "expiry_or_review_date"):
                    assert exception.get(required)
    for exception_id, exception in approved.items():
        assert exception.get("status") == "APPROVED_EXCEPTION"
        for required in ("reviewer", "approval_reference", "approved_at", "rationale", "expiry_or_review_date"):
            assert exception.get(required)


def test_requested_69_and_59_reconciliation_counts_are_preserved():
    summary = json.loads(MANIFEST.read_text(encoding="utf-8"))["reconciliation"]
    assert summary["declared_basis_differences"] == 69
    assert summary["declared_condition_differences"] == 59
