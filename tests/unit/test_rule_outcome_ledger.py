from types import SimpleNamespace

from app.compliance.rule_outcome_ledger import (
    build_rule_outcomes_snapshot,
    hash_rule_outcomes_snapshot,
)


def _rule(rule_id: str, *, statutory_basis="UNVERIFIED CANDIDATE"):
    return SimpleNamespace(
        rule_id=rule_id,
        rule_version="2.2",
        statutory_basis=statutory_basis,
        verification_status="PENDING",
        verified_by=None,
        verified_at=None,
    )


def _flag(rule_id: str, state: str, *, applicability_state=None, conditional_applies=True, statutory_basis="UNVERIFIED CANDIDATE"):
    return SimpleNamespace(
        rule_id=rule_id,
        flag_code=f"{rule_id}_REVIEW",
        state=state,
        eval_state=state,
        conditional_applies=conditional_applies,
        applicability_state=applicability_state,
        applicability_reason=None,
        severity="NOT_EVALUATED",
        description="Evidence review required",
        statutory_basis=statutory_basis,
        detail={},
    )


def test_rule_without_emitted_finding_is_not_evaluated_and_applicability_unknown():
    rows = build_rule_outcomes_snapshot([_rule("AGM-001")], [])
    assert rows[0]["outcome_state"] == "NOT_EVALUATED"
    assert rows[0]["assessment_source"] == "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"
    assert rows[0]["applicability_state"] == "UNKNOWN"
    assert rows[0]["applicability_source"] == "NO_EXPLICIT_ENGINE_DECISION"
    assert "not proof of non-applicability" in rows[0]["finding_applicability_reason"].lower()


def test_engine_finding_state_and_explicit_applicability_are_preserved():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")], [_flag("AGM-001", "UNKNOWN", applicability_state="APPLICABLE", conditional_applies=True)]
    )
    assert rows[0]["outcome_state"] == "UNKNOWN"
    assert rows[0]["assessment_source"] == "ENGINE_FINDING"
    assert rows[0]["applicability_state"] == "APPLICABLE"
    assert rows[0]["applicability_source"] == "ENGINE_EXPLICIT_APPLICABILITY_RESULT"


def test_explicit_not_applicable_result_is_not_inferred_from_missing_finding():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")], [_flag("AGM-001", "NOT_APPLICABLE", applicability_state="NOT_APPLICABLE", conditional_applies=False)]
    )
    assert rows[0]["applicability_state"] == "NOT_APPLICABLE"


def test_conflicting_applicability_results_are_unknown_not_collapsed():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [
            _flag("AGM-001", "NON_COMPLIANT", applicability_state="APPLICABLE", conditional_applies=True),
            _flag("AGM-001", "NOT_APPLICABLE", applicability_state="NOT_APPLICABLE", conditional_applies=False),
        ],
    )
    assert rows[0]["applicability_state"] == "UNKNOWN"
    assert rows[0]["applicability_conflict"] is True
    assert rows[0]["applicability_source"] == "CONFLICTING_ENGINE_APPLICABILITY_RESULTS"


def test_conflicting_findings_are_not_silently_collapsed():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [_flag("AGM-001", "UNKNOWN"), _flag("AGM-001", "NON_COMPLIANT")],
    )
    assert rows[0]["outcome_state"] == "CONTRADICTORY"
    assert len(rows[0]["findings"]) == 2


def test_snapshot_hash_is_stable_and_sensitive_to_state():
    first = build_rule_outcomes_snapshot([_rule("AGM-001")], [])
    second = build_rule_outcomes_snapshot([_rule("AGM-001")], [])
    changed = build_rule_outcomes_snapshot(
        [_rule("AGM-001")], [_flag("AGM-001", "UNKNOWN")]
    )
    assert hash_rule_outcomes_snapshot(first) == hash_rule_outcomes_snapshot(second)
    assert hash_rule_outcomes_snapshot(first) != hash_rule_outcomes_snapshot(changed)


def test_engine_finding_without_active_catalogue_rule_is_preserved_as_unmapped():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")], [_flag("UNKNOWN-999", "UNKNOWN")]
    )
    orphan = next(item for item in rows if item["rule_id"] == "UNKNOWN-999")
    assert orphan["verification_status"] == "UNMAPPED"
    assert orphan["assessment_source"] == "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"



def test_applicability_is_explicit_and_independent_of_findings():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [],
        applicability_results={
            "AGM-001": {
                "status": "APPLICABLE",
                "reason": "Verified scope predicates satisfied",
                "policy_version": "NLC-APPLICABILITY-TEST",
                "fact_evidence": [{"fact_id": "fact-1", "fact_key": "is_active"}],
            }
        },
    )
    assert rows[0]["applicability_status"] == "APPLICABLE"
    assert rows[0]["outcome_state"] == "NOT_EVALUATED"
    assert rows[0]["assessment_source"] == "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"


def test_absent_applicability_result_defaults_to_unknown_even_when_finding_exists():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [_flag("AGM-001", "UNKNOWN")],
    )
    assert rows[0]["applicability_status"] == "UNKNOWN"
    assert rows[0]["applicability_reason"] == "NO_EXPLICIT_APPLICABILITY_RESULT"
    assert rows[0]["outcome_state"] == "UNKNOWN"


def test_applicability_is_included_in_immutable_snapshot_hash():
    applicable = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [],
        applicability_results={"AGM-001": {"status": "APPLICABLE", "reason": "verified"}},
    )
    unknown = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [],
        applicability_results={"AGM-001": {"status": "UNKNOWN", "reason": "missing fact"}},
    )
    assert hash_rule_outcomes_snapshot(applicable) != hash_rule_outcomes_snapshot(unknown)
    assert unknown[0]["applicability_state"] == "UNKNOWN"


def test_emitted_finding_without_explicit_applicability_remains_unknown():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [_flag("AGM-001", "NON_COMPLIANT", conditional_applies=True)],
    )
    assert rows[0]["outcome_state"] == "NON_COMPLIANT"
    assert rows[0]["applicability_state"] == "UNKNOWN"
    assert rows[0]["applicability_source"] == "ENGINE_APPLICABILITY_UNRESOLVED"


def test_scoring_ineligibility_is_not_misreported_as_not_applicable():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")],
        [_flag(
            "AGM-001",
            "UNKNOWN",
            conditional_applies=False,
            applicability_state="UNKNOWN",
        )],
    )
    assert rows[0]["applicability_state"] == "UNKNOWN"
    assert rows[0]["applicability_state"] != "NOT_APPLICABLE"



def test_same_rule_id_with_different_statutory_basis_is_not_attributed_to_catalogue_row():
    rows = build_rule_outcomes_snapshot(
        [
            _rule(
                "INC-001",
                statutory_basis="Section 9, Companies Act 1994 (Bangladesh)",
            )
        ],
        [
            _flag(
                "INC-001",
                "UNKNOWN",
                statutory_basis="Section 23, Companies Act 1994 (Bangladesh)",
            )
        ],
    )
    assert len(rows) == 1
    assert rows[0]["rule_id"] == "INC-001"
    assert rows[0]["findings"] == []
    assert rows[0]["outcome_state"] == "UNKNOWN"
    assert rows[0]["assessment_source"] == "IDENTITY_MISMATCH_NOT_ATTRIBUTED"
    assert rows[0]["identity_conflicts"] == [
        {
            "flag_code": "INC-001_REVIEW",
            "flag_statutory_basis": "Section 23, Companies Act 1994 (Bangladesh)",
            "catalogue_statutory_basis": "Section 9, Companies Act 1994 (Bangladesh)",
            "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
        }
    ]


def test_duplicate_active_catalogue_rule_ids_fail_closed():
    import pytest

    with pytest.raises(ValueError, match="Duplicate active catalogue rule_id"):
        build_rule_outcomes_snapshot(
            [_rule("INC-001"), _rule("INC-001")],
            [],
        )


def test_identity_basis_matching_normalizes_case_and_whitespace():
    rows = build_rule_outcomes_snapshot(
        [_rule("INC-001", statutory_basis="  SECTION   9, Companies Act 1994 ")],
        [_flag(
            "INC-001",
            "UNKNOWN",
            statutory_basis="section 9, companies act 1994",
        )],
    )
    assert rows[0]["assessment_source"] == "ENGINE_FINDING"
    assert rows[0]["identity_conflicts"] == []


def test_catalogue_identity_conflict_is_preserved_without_engine_finding():
    conflict = {
        "rule_id": "INC-001",
        "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
        "binding_reason": "STATUTORY_BASIS_MISMATCH",
        "engine_statutory_basis": "Section 23",
        "catalogue_statutory_basis": "Section 9",
        "catalogue_rule_version": "2.3",
        "catalogue_is_active": True,
    }
    rows = build_rule_outcomes_snapshot(
        [_rule("INC-001")],
        [],
        catalogue_identity_conflicts={"INC-001": conflict},
    )
    assert rows[0]["outcome_state"] == "UNKNOWN"
    assert rows[0]["applicability_status"] == "UNKNOWN"
    assert rows[0]["assessment_source"] == "IDENTITY_MISMATCH_NOT_ATTRIBUTED"
    assert rows[0]["findings"] == []
    assert rows[0]["identity_conflicts"] == [conflict]


def test_inactive_catalogue_identity_is_preserved_as_unmapped_conflict():
    conflict = {
        "rule_id": "INC-002",
        "resolution_status": "UNRESOLVED_STATUTORY_IDENTITY_MISMATCH",
        "binding_reason": "RULE_INACTIVE",
        "engine_statutory_basis": "Section 9",
        "catalogue_statutory_basis": "Section 9",
        "catalogue_rule_version": "legacy",
        "catalogue_is_active": False,
    }
    rows = build_rule_outcomes_snapshot(
        [_rule("INC-001")],
        [],
        catalogue_identity_conflicts={"INC-002": conflict},
    )
    orphan = next(row for row in rows if row["rule_id"] == "INC-002")
    assert orphan["outcome_state"] == "UNKNOWN"
    assert orphan["assessment_source"] == "ENGINE_FINDING_WITHOUT_ACTIVE_CATALOGUE_RULE"
    assert orphan["findings"] == []
    assert orphan["identity_conflicts"] == [conflict]
