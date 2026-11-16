"""Tests for the read-only historical rule-reference inventory."""
from scripts.audit_rule_historical_attribution import classify_reference_match


def test_reference_match_is_never_misrepresented_as_attributed():
    item = classify_reference_match(
        "INC-001", "compliance_evaluation_runs",
        "flags_snapshot", {"id": "run-123"},
    )
    assert item["attribution_status"] == "UNATTRIBUTED"
    assert "does not bind" in item["reason"]


def test_legacy_and_canonical_rule_ids_are_reported_as_distinct_candidates():
    old = classify_reference_match(
        "INC-001", "compliance_flags", "rule_id", {"id": "flag-old"}
    )
    retired = classify_reference_match(
        "INC-002", "compliance_flags", "rule_id", {"id": "flag-legacy"}
    )
    assert old["rule_id"] == "INC-001"
    assert retired["rule_id"] == "INC-002"
    assert old["attribution_status"] == retired["attribution_status"] == "UNATTRIBUTED"
