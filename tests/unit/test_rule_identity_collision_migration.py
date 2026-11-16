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
        "payload_sha256",
        "hashlib.sha256",
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
        "moa_aoa_filed == False",
        "moa_aoa_filed == False",
        "Section 23, Companies Act 1994 (Bangladesh)",
        "form_iii_filed == False AND days_since_incorporation > 28",
        "INC-001 does not match a reviewed historical fingerprint",
        "INC-002 does not match a reviewed historical fingerprint",
        "default_severity='NOT_EVALUATED'",
        "score_impact=0",
        "is_black_override=false",
    ):
        assert marker in source


def test_archive_rls_is_applied_after_archive_and_quarantine_writes():
    source = MIGRATION.read_text(encoding="utf-8")
    final_quarantine = source.index("Legacy INC-002 identity quarantined")
    enable_rls = source.index("ALTER TABLE public.legal_rule_identity_archive ENABLE")
    assert enable_rls > final_quarantine
    assert "ALTER TABLE public.legal_rule_identity_archive FORCE ROW LEVEL SECURITY" in source
    assert "payload_sha256" in source
    assert "ON CONFLICT (legacy_identity_key) DO NOTHING" not in source
