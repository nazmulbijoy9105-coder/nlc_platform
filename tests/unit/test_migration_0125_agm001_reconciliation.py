import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_agm001_migration_is_fingerprint_scoped_and_version_audited():
    migration = (
        ROOT
        / "alembic"
        / "versions"
        / "0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "0125_reconcile_agm001_statutory_basis"' in migration
    assert 'down_revision = "0124_restore_85_rule_catalogue_parity"' in migration
    assert 'LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"' in migration
    assert (
        'CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"'
        in migration
    )
    assert "if _definition(current) != LEGACY_DEFINITION:" in migration
    assert "to_jsonb(rule) AS previous_definition" in migration
    assert "INSERT INTO public.legal_rule_versions" in migration
    assert "'MIGRATION', :migration_revision" in migration
    assert migration.index("INSERT INTO public.legal_rule_versions") < migration.index(
        "UPDATE public.legal_rules"
    )
    assert "AND statutory_basis = :legacy_basis" in migration
    assert "rule_version = :next_version" in migration
    assert "def downgrade() -> None:" in migration
    assert "0125 is forward-only" in migration


def test_agm001_release_redaction_fixture_uses_migrated_catalogue_identity():
    source = (
        ROOT / "tests" / "integration" / "test_services.py"
    ).read_text(encoding="utf-8")
    start = source.index("async def test_evaluate_company_full_pipeline")
    next_boundary = re.compile(r"\n {0,4}(?:@|#|async def |def |class )")
    boundary = next_boundary.search(source, start + 1)
    fixture = source[start : boundary.start() if boundary else None]

    assert "catalogue_rule = catalogue_result.scalar_one()" in fixture
    assert (
        "catalogue_rule.statutory_basis == canonical_agm_001_basis" in fixture
        or "catalogue_rule.statutory_basis == canonical_agm_basis" in fixture
    )
    assert "_catalogue_identity_conflicts([catalogue_rule])" in fixture
    assert '"MATCHED_CATALOGUE_IDENTITY"' in fixture
    assert "\n        catalogue_rule.statutory_basis = " not in fixture
    assert "LegalRule(" not in fixture
    assert fixture.index('"MATCHED_CATALOGUE_IDENTITY"') < fixture.index(
        '["score_impact_applied"] == 0'
    )

def test_agm001_canonical_row_requires_its_own_verified_migration_history():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")

    canonical_branch = migration.index(
        'if current["statutory_basis"] == CANONICAL_BASIS:'
    )
    history_validation = migration.index(
        "_validate_migration_history(bind, current)", canonical_branch
    )
    early_return = migration.index("return", history_validation)
    assert canonical_branch < history_validation < early_return
    assert "if len(history) != 1:" in migration
    assert 'record["actor_type"] != "MIGRATION"' in migration
    assert 'previous.get("statutory_basis") != LEGACY_BASIS' in migration
    assert "_definition(" in migration
    assert "expected_version = _next_version(str(record[\"version\"]))" in migration
    assert 'current_row["rule_version"] != expected_version' in migration


def test_agm001_reconciliation_rejects_any_drift_from_exact_legacy_definition():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")

    assert '"description": (' in migration
    assert '"First AGM not held within 18 months (548 days) of incorporation. "' in migration
    assert '"trigger": "first_agm_held == False AND days_since_incorporation > 548"' in migration
    validation = migration.index("if _definition(current) != LEGACY_DEFINITION:")
    canonical_update = migration.index("UPDATE public.legal_rules")
    assert validation < canonical_update


def test_agm001_reconciliation_uses_version_ledger_without_changing_identity_archive_count():
    migration = (
        ROOT / "alembic/versions/0125_reconcile_agm001_statutory_basis.py"
    ).read_text(encoding="utf-8")
    parity_audit = (
        ROOT / "tools/audit_production_release_parity.py"
    ).read_text(encoding="utf-8")

    assert "INSERT INTO public.legal_rule_versions" in migration
    assert "INSERT INTO public.legal_rule_identity_archive" not in migration
    assert 'result.get("identity_archive_rows") != 2' in parity_audit
