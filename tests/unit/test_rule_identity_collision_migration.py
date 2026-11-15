"""Structural guards for the forward-only rule identity collision migration."""
from pathlib import Path
import ast

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic" / "versions" / "0112_rule_identity_collision_reconciliation.py"

def test_identity_migration_is_chained_after_outcome_ledger():
    source = MIGRATION.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MIGRATION))
    values = {
        node.targets[0].id: ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id in {"revision", "down_revision"}
    }
    assert values == {"revision": "0112_rule_identity_collision_reconciliation", "down_revision": "0111_rule_outcome_ledger"}

def test_identity_migration_archives_before_replacing_and_never_rewrites_history():
    source = MIGRATION.read_text(encoding="utf-8")
    for marker in ("legal_rule_identity_archive", "legacy:INC-001:companies-act-section-9",
                   "legacy:INC-002:companies-act-section-11", "PRESERVED_LEGACY_IDENTITY",
                   "RETIRED_LEGACY_IDENTITY", "AMBIGUOUS_UNLESS_HISTORICAL_SNAPSHOT_BINDS_DEFINITION"):
        assert marker in source
    assert "UPDATE public.compliance_evaluation_runs" not in source
    assert "DELETE FROM public.legal_rules" not in source
    assert "Forward-only" in source

def test_identity_migration_fails_closed_on_unknown_rows_or_foreign_keys():
    source = MIGRATION.read_text(encoding="utf-8")
    for marker in ("Refusing rule identity rewrite while FK dependants exist",
                   "INC-001 has an unrecognized identity; refusing overwrite",
                   "INC-002 has an unrecognized identity; refusing retirement",
                   "INC-001 missing; restore canonical row"):
        assert marker in source