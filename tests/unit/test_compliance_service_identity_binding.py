from types import SimpleNamespace

import pytest

from app.services.compliance_service import (
    _active_catalogue_rule_ids,
    _current_persistable_rule_ids,
    _has_unresolved_catalogue_binding,
    _persistable_output_flags,
    _score_blocking_catalogue_conflicts,
)
from scripts.seed_rules import ILRMF_RULES
from canonical_architecture.rjsc_scope import (
    RJSC_OUT_OF_SCOPE_RULE_IDS,
    is_rjsc_rule_in_scope,
)


def test_rjsc_applicability_uses_only_in_scope_active_ids_and_excludes_held_identity():
    from canonical_architecture.rjsc_scope import RJSC_IN_SCOPE_RULE_IDS

    catalogue_rows = [
        SimpleNamespace(rule_id=rule["rule_id"], is_active=True)
        for rule in ILRMF_RULES
    ]
    active_ids = _active_catalogue_rule_ids(catalogue_rows, {"INC-001"})
    expected_rjsc_ids = {
        rule["rule_id"] for rule in ILRMF_RULES
        if rule["rule_id"] in RJSC_IN_SCOPE_RULE_IDS
    }

    assert len(ILRMF_RULES) == 85
    assert "INC-001" in expected_rjsc_ids
    assert len(active_ids) == len(expected_rjsc_ids) - 1
    assert len(set(active_ids)) == len(active_ids)
    assert "INC-001" not in active_ids
    assert set(active_ids) == expected_rjsc_ids - {"INC-001"}


def test_mismatched_engine_finding_is_not_persisted_over_legacy_rule_identity():
    quarantined = SimpleNamespace(
        rule_id="INC-001",
        detail={"rule_catalogue_binding": "STATUTORY_BASIS_MISMATCH"},
    )
    inactive = SimpleNamespace(
        rule_id="INC-001",
        detail={"rule_catalogue_binding": "RULE_INACTIVE"},
    )
    missing = SimpleNamespace(
        rule_id="INC-002",
        detail={"rule_catalogue_binding": "CATALOGUE_ENTRY_MISSING"},
    )
    ordinary = SimpleNamespace(
        rule_id="AGM-001",
        detail={"rule_catalogue_binding": "MATCHED"},
    )

    assert _has_unresolved_catalogue_binding(quarantined) is True
    assert _has_unresolved_catalogue_binding(inactive) is True
    assert _has_unresolved_catalogue_binding(missing) is True
    assert _has_unresolved_catalogue_binding(ordinary) is False
    assert _persistable_output_flags(
        [quarantined, inactive, missing, ordinary]
    ) == [ordinary]



def test_live_production_catalogue_keeps_inc001_active_and_only_inc002_inactive():
    catalogue_rows = [
        SimpleNamespace(
            rule_id=rule["rule_id"],
            is_active=rule["rule_id"] != "INC-002",
        )
        for rule in ILRMF_RULES
    ]
    if not any(row.rule_id == "INC-002" for row in catalogue_rows):
        catalogue_rows.append(SimpleNamespace(
            rule_id="INC-002",
            is_active=False,
            rule_version="legacy",
            statutory_basis="Legacy inactive rule",
        ))
    active_ids = _active_catalogue_rule_ids(catalogue_rows, set())

    from canonical_architecture.rjsc_scope import RJSC_IN_SCOPE_RULE_IDS

    canonical_ids = {
        rule["rule_id"] for rule in ILRMF_RULES
        if rule["rule_id"] in RJSC_IN_SCOPE_RULE_IDS
    }
    assert "INC-001" in active_ids
    assert {row.rule_id for row in catalogue_rows if not row.is_active} == {"INC-002"}
    assert set(active_ids) == canonical_ids


def test_catalogue_identity_conflicts_are_derived_without_engine_findings():
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import _catalogue_identity_conflicts

    rows = [
        SimpleNamespace(
            rule_id=rule_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=rule.law,
        )
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
    ]
    rows.append(SimpleNamespace(
        rule_id="INC-002",
        rule_version="legacy",
        is_active=False,
        statutory_basis="Legacy inactive rule",
    ))
    target = rows[0]
    target.statutory_basis = "Different statutory basis"

    conflicts = _catalogue_identity_conflicts(rows)
    assert target.rule_id in conflicts
    assert conflicts[target.rule_id]["binding_reason"] == "STATUTORY_BASIS_MISMATCH"
    assert conflicts["INC-002"]["binding_reason"] in {
        "RULE_INACTIVE", "ENGINE_RULE_DEFINITION_MISSING"
    }


def test_catalogue_conflict_quarantines_finding_before_scoring_or_rescue():
    from app.services.compliance_service import _quarantine_catalogue_conflict_findings

    flag = SimpleNamespace(
        rule_id="INC-001",
        detail={},
        statutory_basis="Section 23",
        severity="RED",
        score_impact=10,
        state="NON_COMPLIANT",
        eval_state="VIOLATION",
        is_black_override=True,
        conditional_applies=True,
        applicability_state="APPLICABLE",
        applicability_reason=None,
    )
    conflicts = {
        "INC-001": {
            "binding_reason": "STATUTORY_BASIS_MISMATCH",
            "catalogue_statutory_basis": "Section 9",
        }
    }

    _quarantine_catalogue_conflict_findings([flag], conflicts)

    assert flag.state == "UNKNOWN"
    assert flag.eval_state == "UNKNOWN"
    assert flag.severity.value == "NOT_EVALUATED"
    assert flag.score_impact == 0
    assert flag.is_black_override is False
    assert flag.conditional_applies is False
    assert flag.applicability_state == "UNKNOWN"
    assert flag.detail["rule_catalogue_binding"] == "STATUTORY_BASIS_MISMATCH"


def test_inactive_legacy_catalogue_identity_is_audited_but_does_not_block_score_release():
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import (
        _catalogue_identity_conflicts,
        _score_blocking_catalogue_conflicts,
    )

    rows = [
        SimpleNamespace(
            rule_id=rule_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=rule.law,
        )
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
    ]
    rows.append(SimpleNamespace(
        rule_id="INC-002",
        rule_version="legacy",
        is_active=False,
        statutory_basis="Legacy inactive identity",
    ))

    conflicts = _catalogue_identity_conflicts(rows)

    assert conflicts["INC-002"]["binding_reason"] == "RULE_INACTIVE"
    assert "INC-002" not in _score_blocking_catalogue_conflicts(conflicts)


def test_inactive_canonical_evaluator_identity_blocks_score_release():
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import (
        _catalogue_identity_conflicts,
        _score_blocking_catalogue_conflicts,
    )

    rows = [
        SimpleNamespace(
            rule_id=rule_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=rule.law,
        )
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
    ]
    canonical_rule_id = next(iter(STATUTORY_RULE_REGISTRY))
    next(row for row in rows if row.rule_id == canonical_rule_id).is_active = False

    conflicts = _catalogue_identity_conflicts(rows)

    assert conflicts[canonical_rule_id]["binding_reason"] == "RULE_INACTIVE"
    assert canonical_rule_id in _score_blocking_catalogue_conflicts(conflicts)



def test_conflicted_active_flag_is_not_counted_as_current_and_will_be_cleaned_up():
    conflicted = SimpleNamespace(
        rule_id="INC-001",
        detail={"rule_catalogue_binding": "STATUTORY_BASIS_MISMATCH"},
    )
    current = SimpleNamespace(
        rule_id="AGM-001",
        detail={"rule_catalogue_binding": "MATCHED"},
    )
    current_ids = _current_persistable_rule_ids(
        [conflicted, current],
        {"INC-001"},
    )

    assert current_ids == {"AGM-001"}
    # The persistence query resolves ACTIVE rows whose IDs are not in this set.
    assert "INC-001" not in current_ids


@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_any_out_of_scope_catalogue_conflict_is_inert_for_rjsc_release(rule_id):
    conflicts = {
        rule_id: {
            "rule_id": rule_id,
            "binding_reason": "STATUTORY_BASIS_MISMATCH",
            "catalogue_is_active": True,
        }
    }
    assert _score_blocking_catalogue_conflicts(conflicts) == set()


def test_unknown_active_catalogue_conflict_still_fails_closed():
    conflicts = {
        "UNKNOWN-999": {
            "rule_id": "UNKNOWN-999",
            "binding_reason": "ENGINE_RULE_DEFINITION_MISSING",
            "catalogue_is_active": True,
        }
    }
    assert _score_blocking_catalogue_conflicts(conflicts) == {"UNKNOWN-999"}


def test_duplicate_active_catalogue_identity_fails_closed():
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import _catalogue_identity_conflicts

    rows = [
        SimpleNamespace(
            rule_id=rule_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=rule.law,
        )
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
    ]
    duplicate = SimpleNamespace(
        rule_id=rows[0].rule_id,
        rule_version="duplicate",
        is_active=True,
        statutory_basis=rows[0].statutory_basis,
    )
    with pytest.raises(ValueError, match="Duplicate active catalogue rule_id"):
        _catalogue_identity_conflicts([*rows, duplicate])



@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_out_of_scope_catalogue_row_and_conflict_cannot_change_rjsc_binding_hash_material(rule_id):
    import hashlib
    import json

    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import _rjsc_catalogue_binding_snapshot

    rows = [
        SimpleNamespace(
            rule_id=canonical_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=canonical_rule.law,
            verification_status="PENDING",
        )
        for canonical_id, canonical_rule in STATUTORY_RULE_REGISTRY.items()
        if is_rjsc_rule_in_scope(canonical_id)
    ]
    baseline = _rjsc_catalogue_binding_snapshot(rows, {})
    injected_row = SimpleNamespace(
        rule_id=rule_id,
        rule_version="attacker-controlled-version",
        is_active=True,
        statutory_basis="Injected non-RJSC statutory basis",
        verification_status="VERIFIED",
    )
    injected_conflict = {
        rule_id: {
            "rule_id": rule_id,
            "binding_reason": "STATUTORY_BASIS_MISMATCH",
            "engine_statutory_basis": "External regulator",
            "catalogue_statutory_basis": "Injected non-RJSC statutory basis",
            "catalogue_is_active": True,
        }
    }
    changed = _rjsc_catalogue_binding_snapshot(
        [*rows, injected_row], injected_conflict
    )
    def canonical(value):
        return json.dumps(
            value, sort_keys=True, separators=(",", ":")
        ).encode()

    assert changed == baseline
    assert hashlib.sha256(canonical(changed)).hexdigest() == hashlib.sha256(
        canonical(baseline)
    ).hexdigest()



@pytest.mark.parametrize("rule_id", sorted(RJSC_OUT_OF_SCOPE_RULE_IDS))
def test_duplicate_active_out_of_scope_catalogue_rows_are_inert(rule_id):
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import (
        _active_catalogue_rows_for_rjsc_ledger,
        _catalogue_identity_conflicts,
        _score_blocking_catalogue_conflicts,
    )

    rows = [
        SimpleNamespace(
            rule_id=canonical_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=canonical_rule.law,
        )
        for canonical_id, canonical_rule in STATUTORY_RULE_REGISTRY.items()
    ]
    out_of_scope = SimpleNamespace(
        rule_id=rule_id,
        rule_version="duplicate",
        is_active=True,
        statutory_basis="External-regulator basis",
    )
    duplicated = [*rows, out_of_scope]
    conflicts = _catalogue_identity_conflicts(duplicated)
    assert rule_id not in _score_blocking_catalogue_conflicts(conflicts)
    assert len(_active_catalogue_rows_for_rjsc_ledger(duplicated)) == len(
        _active_catalogue_rows_for_rjsc_ledger(rows)
    )

@pytest.mark.parametrize(
    "field,drifted_value",
    [
        ("rule_name", "Operator-renamed AGM rule"),
        ("rule_type", "POLICY"),
        ("description", "First AGM deadline: fixed 548 days"),
        (
            "rule_condition",
            {
                "check_fn": "check_agm_001",
                "trigger": "first_agm_held == False AND days_since_incorporation > 548",
                "data_points": ["incorporation_date", "first_agm_held", "agm_count"],
            },
        ),
    ],
)
def test_agm001_matching_citation_does_not_hide_definition_drift(field, drifted_value):
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import _catalogue_identity_conflicts

    canonical_agm = next(rule for rule in ILRMF_RULES if rule["rule_id"] == "AGM-001")
    rows = [
        SimpleNamespace(
            rule_id=rule_id,
            rule_version="2.3",
            is_active=True,
            statutory_basis=rule.law,
            rule_name=canonical_agm["rule_name"] if rule_id == "AGM-001" else rule_id,
            rule_type=canonical_agm["rule_type"] if rule_id == "AGM-001" else "DEADLINE",
            description=canonical_agm["description"] if rule_id == "AGM-001" else "test",
            rule_condition=canonical_agm["rule_condition"] if rule_id == "AGM-001" else {},
        )
        for rule_id, rule in STATUTORY_RULE_REGISTRY.items()
    ]
    agm_row = next(row for row in rows if row.rule_id == "AGM-001")
    assert agm_row.statutory_basis == STATUTORY_RULE_REGISTRY["AGM-001"].law
    assert "AGM-001" not in _catalogue_identity_conflicts(rows)

    setattr(agm_row, field, drifted_value)
    conflicts = _catalogue_identity_conflicts(rows)

    assert conflicts["AGM-001"]["binding_reason"] == "RULE_DEFINITION_MISMATCH"
    assert conflicts["AGM-001"]["catalogue_is_active"] is True
    assert "AGM-001" in _score_blocking_catalogue_conflicts(conflicts)

def test_catalogue_identity_query_projects_only_binding_columns():
    from app.models.rules import LegalRule
    from app.services.compliance_service import _catalogue_identity_query

    expected_columns = (
        "rule_id",
        "rule_version",
        "is_active",
        "statutory_basis",
        "verification_status",
    )
    descriptions = _catalogue_identity_query().column_descriptions

    assert tuple(description["name"] for description in descriptions) == expected_columns
    assert all(
        description["expr"] is getattr(LegalRule, name)
        and description["entity"] is LegalRule
        for description, name in zip(descriptions, expected_columns, strict=True)
    )


def test_evaluation_snapshot_query_loads_complete_legal_rule_records():
    from app.models.rules import LegalRule
    from app.services.compliance_service import _catalogue_snapshot_query

    (description,) = _catalogue_snapshot_query().column_descriptions

    assert description["expr"] is LegalRule
    assert description["entity"] is LegalRule
    assert hasattr(LegalRule, "verified_by")
    assert hasattr(LegalRule, "verified_at")

def test_agm001_missing_definition_fields_fail_closed_without_attribute_error():
    from canonical_architecture.statutory_rules import STATUTORY_RULE_REGISTRY
    from app.services.compliance_service import _catalogue_identity_conflicts

    row = SimpleNamespace(
        rule_id="AGM-001",
        rule_version="2.3",
        is_active=True,
        statutory_basis=STATUTORY_RULE_REGISTRY["AGM-001"].law,
    )

    conflicts = _catalogue_identity_conflicts([row])

    assert conflicts["AGM-001"]["binding_reason"] == "RULE_DEFINITION_MISMATCH"
    assert conflicts["AGM-001"]["catalogue_is_active"] is True
