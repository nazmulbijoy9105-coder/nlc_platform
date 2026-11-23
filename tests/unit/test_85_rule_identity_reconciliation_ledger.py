"""Integrity tests for the preserved 85-rule ledger and current production follow-up."""
import hashlib
import json
from pathlib import Path

from scripts.seed_rules import ILRMF_RULES

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "legal" / "85_rule_identity_definition_reconciliation_2026-11-23.json"
ORIGINAL_LEDGER_SHA256 = "d8044d42e95be5f72c6fb430d808ec51e532e9c6c3e6e7c5a486f0b5d70baa2e"


def _stable(value):
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


def _original_payload_sha256(ledger):
    original = {key: value for key, value in ledger.items() if key != "follow_up_snapshots"}
    canonical = json.dumps(original, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _latest(ledger):
    snapshots = ledger["follow_up_snapshots"]
    assert snapshots
    return snapshots[-1]


def test_original_provenance_and_85_rule_history_are_preserved():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))

    # The original 1MB ledger contains the earlier production capture,
    # provenance/source workpack, interval analysis and runtime CI evidence.
    assert ledger["repository"]["commit"] == "b06495678eb564eea52f44c3bafd174d7180f7df"
    assert len(ledger["rules"]) == 85
    assert len(ledger["rules"]) == len({row["rule_id"] for row in ledger["rules"]})
    assert ledger["revision_readiness"]["source_workpack_records"] == 85
    assert ledger["revision_readiness"]["operating_interval_records"] == 85
    assert ledger["revision_readiness"]["verified_effective_dated_revisions"] == 0
    assert ledger["runtime_coverage"]["expected_unique_ids"] == 85
    assert ledger["runtime_coverage"]["emitted_unique_ids"] == 85
    assert _original_payload_sha256(ledger) == ORIGINAL_LEDGER_SHA256


def test_follow_up_snapshot_covers_exactly_current_main_85_engine_ids():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    snapshot = _latest(ledger)
    expected = {rule["rule_id"] for rule in ILRMF_RULES}
    rows = snapshot["rules"]
    actual = [row["rule_id"] for row in rows]

    assert len(rows) == 85
    assert len(set(actual)) == 85
    assert set(actual) == expected
    assert snapshot["repository"]["commit"] == "7fa78ce19d501f2991aed7d25d7572d6a4996cd5"
    assert snapshot["summary"]["current_main_seed_rules"] == 85


def test_follow_up_preserves_each_definition_and_leaves_identity_unresolved():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    snapshot = _latest(ledger)
    seed = {rule["rule_id"]: rule for rule in ILRMF_RULES}

    for row in snapshot["rules"]:
        rule_id = row["rule_id"]
        assert _stable(row["main_definition"]) == _stable(seed[rule_id])
        assert row["production_definition"]["rule_id"] == rule_id
        assert row["identity_resolution"] == "UNRESOLVED_PENDING_INDIVIDUAL_REVIEW"
        assert row["historical_finding_attribution"] == "UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW"
        assert row["effective_dated_revision"] == "NOT_CREATED_SOURCE_AND_EFFECTIVE_DATE_REVIEW_REQUIRED"


def test_inc001_and_inc002_remain_separate_legacy_identity_cases():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    snapshot = _latest(ledger)
    inc001 = next(row for row in snapshot["rules"] if row["rule_id"] == "INC-001")
    legacy = snapshot["additional_legacy_identities"]

    assert "rule_name" in inc001["different_fields"]
    assert len(legacy) == 1
    assert legacy[0]["rule_id"] == "INC-002"
    assert legacy[0]["identity_resolution"] == "QUARANTINED_LEGACY_IDENTITY_REQUIRES_RECORD_LEVEL_REVIEW"
    assert "INC-002" not in {rule["rule_id"] for rule in ILRMF_RULES}
    assert snapshot["identity_and_release_state"]["inc001"]["production_is_active"] is True
    assert snapshot["identity_and_release_state"]["inc002"]["production_is_active"] is False


def test_follow_up_definition_difference_counts_match_the_stored_snapshots():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    snapshot = _latest(ledger)
    fields = snapshot["comparison"]["fields"]
    field_counts = {}
    exact_matches = 0
    differing_rows = 0

    for row in snapshot["rules"]:
        source = row["main_definition"]
        production = row["production_definition"]
        expected_differences = [
            field for field in fields
            if _stable(source.get(field)) != _stable(production.get(field))
        ]
        assert row["different_fields"] == expected_differences
        if expected_differences:
            differing_rows += 1
        else:
            exact_matches += 1
        for field in expected_differences:
            field_counts[field] = field_counts.get(field, 0) + 1

    assert snapshot["summary"]["rules_with_exact_definition_match"] == exact_matches
    assert snapshot["summary"]["rules_with_any_definition_difference"] == differing_rows
    assert snapshot["summary"]["per_field_mismatch_counts"] == field_counts


def test_catalogue_activation_is_not_misrepresented_as_identity_or_legal_approval():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    snapshot = _latest(ledger)
    state = snapshot["identity_and_release_state"]

    inc001 = state["inc001"]
    assert inc001["production_is_active"] is True
    assert inc001["production_verification_status"] == "PENDING"
    assert inc001["production_severity"] == "NOT_EVALUATED"
    assert inc001["canonical_candidate_identity_status"] == "QUARANTINED"
    assert inc001["alias_resolution"] == "UNRESOLVED"
    assert inc001["archived_identity_preserved"] is True

    inc002 = state["inc002"]
    assert inc002["production_is_active"] is False
    assert inc002["production_verification_status"] == "PENDING"
    assert inc002["archived_identity_preserved"] is True

    assert state["identity_cohort_interpretation"]["release_state"].startswith(
        "Production catalogue shows zero VERIFIED legal_rules"
    )
    assert snapshot["safety_decision"]["production_database_changed"] is False
    assert snapshot["safety_decision"]["historical_ids_changed"] is False
    assert snapshot["safety_decision"]["finding_or_evidence_references_rebound"] is False
