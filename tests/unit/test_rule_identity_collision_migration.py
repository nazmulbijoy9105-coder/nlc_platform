"""Structural guards for the forward-only rule identity collision migration."""
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


def test_identity_migration_archives_and_never_rewrites_historical_findings():
    source = MIGRATION.read_text(encoding="utf-8")
    for marker in (
        "legal_rule_identity_archive",
        "legacy:INC-001:companies-act-section-9",
        "legacy:INC-002:companies-act-section-11",
        "PRESERVED_LEGACY_IDENTITY",
        "RETIRED_LEGACY_IDENTITY",
        "AMBIGUOUS_UNLESS_HISTORICAL_SNAPSHOT_BINDS_DEFINITION",
        "historical findings remain unresolved until independently attributed",
    ):
        assert marker in source
    assert "UPDATE public.compliance_evaluation_runs" not in source
    assert "UPDATE public.compliance_flags" not in source
    assert "DELETE FROM public.legal_rules" not in source
    assert "Forward-only" in source


def test_identity_migration_checks_schema_and_fails_closed_on_unknown_rows():
    source = MIGRATION.read_text(encoding="utf-8")
    for marker in (
        "REQUIRED_RULE_COLUMNS",
        "missing columns:",
        "Refusing rule identity rewrite while FK dependants exist",
        "INC-001 has an unrecognized or partially canonical identity",
        "INC-002 has an unrecognized or incomplete identity",
        "INC-001 missing; restore canonical row",
    ):
        assert marker in source
