"""Structural guards for safe legacy identity quarantine."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic" / "versions" / "0115_rule_identity_collision_reconciliation.py"


def _revision_values(source):
    tree = ast.parse(source)
    return {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"revision", "down_revision"}
    }


def test_identity_migration_uses_unique_revision_after_current_head():
    values = _revision_values(MIGRATION.read_text(encoding="utf-8"))
    assert values == {
        "revision": "0115_rule_identity_collision_reconciliation",
        "down_revision": "0114_annual_return_filing_status_provenance",
    }


def test_identity_migration_archives_and_quarantines_without_rewriting_identity():
    source = MIGRATION.read_text(encoding="utf-8")
    for marker in (
        "legal_rule_identity_archive",
        "legacy:INC-001:preserved-original-definition",
        "legacy:INC-002:preserved-original-definition",
        "QUARANTINED_LEGACY_IDENTITY",
        "UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW",
        "Historical references remain attached to the",
        "INC001_LEGACY_FINGERPRINTS",
        "INC002_LEGACY_FINGERPRINTS",
    ):
        assert marker in source
    assert "Refusing rule identity rewrite while FK dependants exist" not in source
    assert "UPDATE public.compliance_evaluation_runs" not in source
    assert "UPDATE public.compliance_flags" not in source
    assert "DELETE FROM public.legal_rules" not in source
    assert "SET rule_name=" not in source
    assert "SET statutory_basis=" not in source
    assert "SET rule_condition=" not in source
    assert "Forward-only" in source


def test_identity_migration_checks_schema_and_known_legacy_fingerprints():
    source = MIGRATION.read_text(encoding="utf-8")
    for marker in (
        "REQUIRED_RULE_COLUMNS",
        "missing columns:",
        "certificate_obtained == False",
        "moa_aoa_filed == False",
        "moa_filed == False OR aoa_filed == False",
        "form_iii_filed == False",
        "INC-001 does not match a reviewed historical fingerprint",
        "INC-002 does not match a reviewed historical fingerprint",
        "default_severity='NOT_EVALUATED'",
        "score_impact=0",
        "is_black_override=false",
    ):
        assert marker in source
