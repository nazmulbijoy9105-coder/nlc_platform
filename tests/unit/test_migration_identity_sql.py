from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fixes" / "01_migration_identity.sql"
README = Path(__file__).resolve().parents[2] / "scripts" / "fixes" / "README.md"


def test_migration_identity_sql_has_no_literal_escaped_newline_sequences():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "\\n" not in source


def test_pre_0050_restore_can_create_private_schema_with_migration_owner():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "schema_name = 'nlc_private'" in source
    assert "CREATE SCHEMA nlc_private AUTHORIZATION nlc_migration_owner" in source
    assert "Required migration schema % is missing" in source


def test_migration_user_is_non_inheriting_and_not_rls_bypass():
    source = SCRIPT.read_text(encoding="utf-8")
    assert "ALTER ROLE nlc_migration_user LOGIN" in source
    assert "NOINHERIT NOBYPASSRLS NOREPLICATION" in source
    assert "WITH ADMIN FALSE, INHERIT FALSE, SET TRUE" in source


def test_legacy_runbook_warns_against_production_application():
    source = README.read_text(encoding="utf-8")
    assert "Do not apply its Steps 1-5 to production" in source
    assert "pinned isolated restore branch" in source
