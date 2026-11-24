from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKPACK = ROOT / "docs" / "legal" / "85_rule_source_and_evidence_workpack_v1.json"


def test_85_rule_source_evidence_workpack_is_complete_as_an_inventory_and_fail_closed() -> None:
    data = json.loads(WORKPACK.read_text(encoding="utf-8"))

    assert data["jurisdiction"] == "BD"
    assert data["rule_count"] == 85
    assert data["release_effect"] == "NONE"
    assert data["coverage"]["rules"] == 85
    assert len(data["rules"]) == 85
    rule_ids = [item["rule_id"] for item in data["rules"]]
    assert len(set(rule_ids)) == 85
    assert rule_ids == sorted(rule_ids)

    for rule in data["rules"]:
        assert rule["statutory_chain"]["primary_instrument"]
        assert rule["statutory_chain"]["operative_interval"]["status"] == (
            "UNRESOLVED_RULE_SPECIFIC_INTERVAL"
        )
        assert rule["seed_rule_claim"]["seed_fact_inputs"]
        assert rule["evidence_contract"]["evidence_roles"]
        assert rule["evidence_contract"]["evidence_role_status"] == (
            "CANDIDATE_EVIDENCE_ROLES_PRESENT_ISSUER_VERIFICATION_REQUIRED"
        )
        assert rule["applicability"]["required_facts"]
        assert all(
            fact["candidate_evidence_contract"]
            and fact["candidate_evidence_contract"]["collection_procedure"]
            and fact["candidate_evidence_contract"]["verification_standard"]
            for fact in rule["applicability"]["required_facts"]
        )
        assert rule["release"]["legal_review"] == "REVIEW_REQUIRED"
        assert rule["release"]["product_decision"] == "NOT_REVIEWED"
        assert rule["release"]["score_eligible"] is False

        for role in rule["evidence_contract"]["evidence_roles"]:
            assert role["issuer_status"] in {
                "NOT_INDEPENDENTLY_VERIFIED",
                "ISSUER_UNRESOLVED",
            }
            assert role["collection_procedure"]
            assert role["verification_standard"]

    # Preserve the known historical/canonical citation conflict; do not erase it.
    agm005 = next(item for item in data["rules"] if item["rule_id"] == "AGM-005")
    assert "Section 89" in agm005["recorded_statutory_basis"]
    assert "Section 85(2)(b)" in agm005["current_canonical_source_claim"]["law"]
    agm005_fact_keys = {
        fact["fact_key"] for fact in agm005["applicability"]["required_facts"]
    }
    assert {
        "company_type",
        "agm_held_this_cycle",
        "member_count",
        "members_present_at_agm",
        "agm_attendance_verified",
        "agm_attendance_evidence_ref",
        "agm_quorum_basis_verified",
        "agm_quorum_evidence_ref",
        "agm_quorum_required",
    } <= agm005_fact_keys
    assert all(
        fact["mapping_status"]
        in {
            "CANDIDATE_MAPPING_REQUIRES_ISSUER_AUTHENTICATION",
            "UNRESOLVED_EVIDENCE_TYPE_REQUIRES_COUNSEL",
        }
        for fact in agm005["applicability"]["required_facts"]
    )


    # The formerly generic evidence placeholders now have rule-specific candidate contracts.
    unresolved = [
        (rule["rule_id"], fact["fact_key"])
        for rule in data["rules"]
        for fact in rule["applicability"]["required_facts"]
        if fact["mapping_status"] == "UNRESOLVED_EVIDENCE_TYPE_REQUIRES_COUNSEL"
    ]
    assert unresolved == []
    resolved_fact_keys = {
        (rule["rule_id"], fact["fact_key"])
        for rule in data["rules"]
        for fact in rule["applicability"]["required_facts"]
    }
    assert ("AGM-003", "short_notice_consent_evidence_ref") in resolved_fact_keys
    assert ("AUD-001", "first_auditor_appointed") in resolved_fact_keys
    assert ("BOD-002", "board_meeting_notice_given") in resolved_fact_keys
    assert ("CAP-002", "registrar_extension_evidence_ref") in resolved_fact_keys
    assert ("DIR-001", "appointment_delay_days") in resolved_fact_keys
    assert ("TAX-002", "annual_turnover_bdt") in resolved_fact_keys
    assert ("TR-003", "aoa_transfer_restriction") in resolved_fact_keys
    assert ("BOD-003", "board_minutes_prepared") in resolved_fact_keys
    assert ("CAP-001", "articles_authority_evidence_ref") in resolved_fact_keys
    assert ("DEF-001", "evidence_ref") in resolved_fact_keys
    assert all(
        fact["candidate_evidence_contract"]["evidence_type"]
        != "RULE_SPECIFIC_PRIMARY_EVIDENCE_REQUIRED"
        for rule in data["rules"]
        for fact in rule["applicability"]["required_facts"]
    )

    # No workpack entry can silently become a legal or product approval.
    assert data["coverage"]["independently_verified_issuers"] == 0
    assert data["coverage"]["complete_fact_to_evidence_mappings"] == 0
    assert data["coverage"]["approved_rules"] == 0
    assert data["coverage"]["seed_rule_claims"] == 85
    assert data["coverage"]["seed_fact_candidate_rules"] == 85
    assert data["coverage"]["fact_inventory_rules"] == 85
    assert data["coverage"]["rules_with_candidate_evidence_roles"] == 85
    assert data["coverage"]["fact_records_with_candidate_evidence_contract"] == 292
    assert data["coverage"]["fact_records_unresolved_evidence_type"] == 0
    assert sum(len(rule["evidence_contract"]["evidence_roles"]) for rule in data["rules"]) == 304
    assert data["coverage"]["complete_fact_to_evidence_mappings"] == 0
