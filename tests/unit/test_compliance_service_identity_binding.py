from types import SimpleNamespace

from app.services.compliance_service import (
    _active_catalogue_rule_ids,
    _has_unresolved_catalogue_binding,
    _persistable_output_flags,
)
from scripts.seed_rules import ILRMF_RULES


def test_85_rule_catalogue_keeps_84_canonical_active_ids_when_inc001_is_held():
    catalogue_rows = [
        SimpleNamespace(rule_id=rule["rule_id"], is_active=True)
        for rule in ILRMF_RULES
    ]
    active_ids = _active_catalogue_rule_ids(catalogue_rows, {"INC-001"})

    assert len(ILRMF_RULES) == 85
    assert len(active_ids) == 84
    assert "INC-001" not in active_ids
    assert set(active_ids) == {rule["rule_id"] for rule in ILRMF_RULES} - {"INC-001"}


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
    active_ids = _active_catalogue_rule_ids(catalogue_rows, set())

    canonical_ids = {rule["rule_id"] for rule in ILRMF_RULES}
    assert "INC-001" in active_ids
    assert {row.rule_id for row in catalogue_rows if not row.is_active} == {"INC-002"}
    assert set(active_ids) == canonical_ids - {"INC-002"}


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
