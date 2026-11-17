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


def _flag(rule_id: str, state: str):
    return SimpleNamespace(
        rule_id=rule_id,
        flag_code=f"{rule_id}_REVIEW",
        state=state,
        eval_state=state,
        severity="NOT_EVALUATED",
        description="Evidence review required",
        statutory_basis="UNVERIFIED CANDIDATE",
    )


def test_rule_without_emitted_finding_is_not_evaluated_not_compliant():
    rows = build_rule_outcomes_snapshot([_rule("AGM-001")], [])
    assert rows[0]["outcome_state"] == "NOT_EVALUATED"
    assert rows[0]["assessment_source"] == "NO_FINDING_EMITTED_NOT_PROOF_OF_COMPLIANCE"


def test_engine_finding_state_is_preserved():
    rows = build_rule_outcomes_snapshot(
        [_rule("AGM-001")], [_flag("AGM-001", "UNKNOWN")]
    )
    assert rows[0]["outcome_state"] == "UNKNOWN"
    assert rows[0]["assessment_source"] == "ENGINE_FINDING"


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
