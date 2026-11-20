from types import SimpleNamespace

from app.compliance.rule_outcome_ledger import (
    build_rule_outcomes_snapshot,
    hash_rule_outcomes_snapshot,
)


def _rule(rule_id: str):
    return SimpleNamespace(
        rule_id=rule_id,
        rule_version="2.2",
        statutory_basis="UNVERIFIED CANDIDATE",
        verification_status="PENDING",
        verified_by=None,
        verified_at=None,
    )


def _flag(rule_id: str, state: str, *, applicability_state=None, conditional_applies=True):
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
        statutory_basis="UNVERIFIED CANDIDATE",
        detail={},
    )


def test_rule_without_emitted_finding_is_not_evaluated_and_applicability_unknown():
    rows = build_rule_outcomes_snapshot([_rule("AGM-001")], [])
    assert rows[0]["outcome_state"] == "NOT_EVALUATED"
    assert rows[0]["assessment_source"] == "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"
    assert rows[0]["applicability_state"] == "UNKNOWN"
    assert rows[0]["applicability_source"] == "NO_EXPLICIT_ENGINE_DECISION"
    assert "not proof of non-applicability" in rows[0]["applicability_reason"].lower()


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
    assert orphan["applicability_state"] == "UNKNOWN"


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
