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
