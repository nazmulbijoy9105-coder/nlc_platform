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
    next_test = source.find("\nasync def test_", start + 1)
    fixture = source[start:next_test if next_test != -1 else None]

    assert "catalogue_rule = catalogue_result.scalar_one()" in fixture
    assert "catalogue_rule.statutory_basis == canonical_agm_basis" in fixture
    assert "_catalogue_identity_conflicts([catalogue_rule])" in fixture
    assert '"MATCHED_CATALOGUE_IDENTITY"' in fixture
    assert "\n        catalogue_rule.statutory_basis = " not in fixture
    assert "LegalRule(" not in fixture
    assert fixture.index('"MATCHED_CATALOGUE_IDENTITY"') < fixture.index(
        '["score_impact_applied"] == 0'
    )
