"""Integrity tests for the preserved 85-rule ledger and current production follow-up."""
import hashlib
import json
from pathlib import Path

from scripts.seed_rules import ILRMF_RULES

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "docs" / "legal" / "85_rule_identity_definition_reconciliation_2026-11-23.json"
HISTORICAL_RULES_SHA256 = "cd51f59299d5d8ae760459ada6ea758335de1dcce2c4767485f694e5db04165c"


def _stable(value):
    if isinstance(value, dict):
        return {key: _stable(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_stable(item) for item in value]
    return value


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
    historical_payload = json.dumps(
        ledger["rules"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    assert hashlib.sha256(historical_payload.encode("utf-8")).hexdigest() == (
        HISTORICAL_RULES_SHA256
    )
    assert ledger["revision_readiness"]["source_workpack_records"] == 85
    assert ledger["revision_readiness"]["operating_interval_records"] == 85
    assert ledger["revision_readiness"]["verified_effective_dated_revisions"] == 0
    assert ledger["runtime_coverage"]["expected_unique_ids"] == 85
    assert ledger["runtime_coverage"]["emitted_unique_ids"] == 85


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


def test_source_workpack_rebase_covers_all_85_and_identifies_only_four_material_cases():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    snapshot = _latest(ledger)
    rebase = snapshot["source_workpack_rebase"]
    assert len(rebase["rules"]) == 85
    assert len({row["rule_id"] for row in rebase["rules"]}) == 85
    assert rebase["summary"]["rules_with_any_seed_claim_drift"] == 3
    assert rebase["summary"]["seed_claim_exact_rules"] == 82
    assert rebase["summary"]["rules_with_current_canonical_source_claim_drift"] == 4
    assert rebase["summary"]["current_source_claim_exact_rules"] == 81
    assert {
        row["rule_id"] for row in rebase["material_discrepancies"]
    } == {"REG-002", "REG-003", "LBR-001", "MEM-001"}


def test_source_workpack_rebase_does_not_invent_effective_dates_or_legal_approval():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rebase = _latest(ledger)["source_workpack_rebase"]
    summary = rebase["summary"]

    assert summary["rules_with_resolved_rule_specific_intervals"] == 0
    assert summary["rules_with_non_exhaustive_amendment_history"] == 85
    assert summary["located_primary_record_anchors"] == 26
    assert summary["independently_authenticated_issuers"] == 0
    assert summary["source_artifact_sha256_captured"] == 0
    assert summary["legal_counsel_approved_rules"] == 0
    assert summary["fact_to_evidence_complete_mappings"] == 0
    assert summary["legal_revisions_created"] == 0

    for row in rebase["rules"]:
        assert row["operating_interval"]["from"] is None
        assert row["operating_interval"]["to_exclusive"] is None
        assert row["operating_interval"]["status"] == "UNRESOLVED_RULE_SPECIFIC_INTERVAL"
        assert row["provenance"]["operative_effective_date_status"] == "UNRESOLVED"
        assert row["provenance"]["legal_review_status"] == "REVIEW_REQUIRED"
        assert row["release"]["score_eligible"] is False


def test_primary_source_candidates_are_linked_without_promoting_them_to_effective_intervals():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rebase = _latest(ledger)["source_workpack_rebase"]
    events = rebase["source_event_candidates"]

    assert events["REG003"][0]["provisions"] == ["41(1)", "89(4)", "174(1)"]
    assert "Section 89(4)" in rebase["legal_source_review_notes"]["REG003"]
    assert "Board-minute location rule" in rebase["legal_source_review_notes"]["REG003"]

    labour = events["LBR001"]
    act = next(item for item in labour if item["instrument"] == "Bangladesh Labour (Amendment) Act 2026")
    rules = next(item for item in labour if item["instrument"] == "Bangladesh Labour (Amendment) Rules 2026")
    assert act["publication_date"] == "2026-04-10"
    assert act["commencement"] == "In force at once"
    assert act["provisions"] == ["326(1)(b)"]
    assert rules["publication_date"] == "2026-02-16"
    assert "NO_AMENDMENT_TO_RULES_354_355" in rules["source_status"]

    members = events["MEM001"][0]
    assert members["candidate_commencement_date"] == "1994-12-01"
    assert members["provisions"] == ["222", "223"]

    # Candidate publication/commencement dates are not rule-specific operative intervals.
    for row in rebase["rules"]:
        assert row["operating_interval"]["from"] is None
        assert row["operating_interval"]["to_exclusive"] is None


def test_four_workpack_discrepancies_are_individually_classified_without_legal_release():
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    rebase = _latest(ledger)["source_workpack_rebase"]
    claims = rebase["current_main_statutory_claims"]
    dispositions = rebase["individual_discrepancy_dispositions"]

    assert set(claims) == {"REG-002", "REG-003", "LBR-001", "MEM-001"}
    assert set(dispositions) == set(claims)
    assert all(claim["provision_status"] == "RECONCILE" for claim in claims.values())
    assert all(claim["severity"] == "NOT_EVALUATED" for claim in claims.values())
    assert all(claim["score_impact"] == 0 for claim in claims.values())

    assert "Section 34(2) is a penalty provision" in claims["REG-003"]["requirement"]
    assert "Do not infer a breach" in claims["REG-003"]["requirement"]
    assert "unresolved renewal-term interaction" in claims["LBR-001"]["requirement"]
    assert "more than six months" in claims["MEM-001"]["requirement"]
    assert "knew of the shortfall" in claims["MEM-001"]["requirement"]
    assert all(
        item["production_definition_change"] == "NOT_AUTHORIZED"
        for item in dispositions.values()
    )
