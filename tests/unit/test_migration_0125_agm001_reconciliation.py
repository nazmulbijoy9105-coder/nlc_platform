from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_agm001_migration_is_fingerprint_scoped_and_forward_only():
    migration = (
        ROOT
        / "alembic"
        / "versions"
        / "0125_reconcile_agm001_catalogue_identity.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "0125_reconcile_agm001_catalogue_identity"' in migration
    assert 'down_revision = "0124_restore_85_rule_catalogue_parity"' in migration
    assert 'LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"' in migration
    assert (
        'CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"'
        in migration
    )
    assert '"rule_condition": LEGACY_CONDITION' in migration
    assert "if observed_definition != expected_definition:" in migration
    assert "refusing to overwrite a conflicting definition" in migration
    assert "to_jsonb(r) AS payload" in migration
    assert "payload_sha256" in migration
    assert migration.index("INSERT INTO public.{ARCHIVE_TABLE}") < migration.index(
        "UPDATE public.legal_rules"
    )
    assert "AND statutory_basis = :legacy_basis" in migration
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
    assert "catalogue_rule.statutory_basis =" not in fixture
    assert "LegalRule(" not in fixture
    assert fixture.index('"MATCHED_CATALOGUE_IDENTITY"') < fixture.index(
        '["score_impact_applied"] == 0'
    )
