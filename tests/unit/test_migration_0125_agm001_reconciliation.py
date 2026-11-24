from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    ROOT
    / "alembic"
    / "versions"
    / "0125_reconcile_agm001_catalogue_identity.py"
)
INTEGRATION_TEST = ROOT / "tests" / "integration" / "test_services.py"


def test_agm001_reconciliation_is_limited_to_the_known_migrated_basis():
    source = MIGRATION.read_text(encoding="utf-8")

    assert 'LEGACY_BASIS = "Section 81, Companies Act 1994 (Bangladesh)"' in source
    assert 'CANONICAL_BASIS = "Section 81(1), Companies Act 1994 (Bangladesh)"' in source
    assert "if current_basis != LEGACY_BASIS:" in source
    assert "refusing to " in source
    assert "overwrite a conflicting legal definition" in source
    assert "AND statutory_basis = :legacy_basis" in source


def test_agm001_reconciliation_archives_the_complete_before_image():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "SELECT to_jsonb(r) AS payload" in source
    assert "FOR UPDATE" in source
    assert "hashlib.sha256" in source
    assert "INSERT INTO public.legal_rule_identity_archive" in source
    assert "'CANONICAL_BASIS_RECONCILIATION'" in source
    assert "'UNATTRIBUTED_PENDING_RECORD_LEVEL_REVIEW'" in source


def test_release_redaction_fixture_uses_migrated_catalogue_without_mutating_it():
    source = INTEGRATION_TEST.read_text(encoding="utf-8")
    marker = 'canonical_agm_basis = STATUTORY_RULE_REGISTRY["AGM-001"].law'
    pos = source.index(marker)
    end = source.index("mock_engine.evaluate.assert_called_once()", pos)
    fixture = source[pos:end]

    assert "catalogue_rule.statutory_basis = canonical_agm_basis" not in fixture
    assert "MATCHED_CATALOGUE_IDENTITY" in fixture
    assert "score_impact_applied" in fixture
    assert "NOT_EVALUATED_PRODUCT_SCORING_DISABLED" in fixture
