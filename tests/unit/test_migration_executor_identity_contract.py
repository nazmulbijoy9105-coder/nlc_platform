from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_ENV = ROOT / "alembic" / "env.py"


def test_production_migrations_require_an_explicit_migration_url():
    source = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert 'if is_production and not migration_url:' in source
    assert "MIGRATION_DATABASE_URL is required in production/Render" in source
    assert "DATABASE_URL fallback is disabled for migrations" in source


def test_production_migration_login_is_separate_from_owner_privileges():
    source = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert 'session_user != "nlc_migration_user"' in source
    assert 'current_user != session_user' in source
    assert "rolcanlogin, rolsuper, rolcreatedb, rolcreaterole" in source
    assert "NOCREATEDB" in source
    assert "NOCREATEROLE" in source
    assert "NOBYPASSRLS" in source


def test_migration_owner_is_non_login_and_assumed_only_with_set_option():
    source = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "nlc_migration_owner" in source
    assert "rolcanlogin, rolsuper, rolcreatedb, rolcreaterole" in source
    assert "membership is None or tuple(membership) != (False, False, True)" in source
    assert 'SET ROLE nlc_migration_owner' in source
    assert 'assumed_role != "nlc_migration_owner"' in source


def test_migration_preflight_requires_object_ownership_before_ddl():
    source = ALEMBIC_ENV.read_text(encoding="utf-8")

    assert "owns_rescue_audit_log" in source
    assert "owns_alembic_version" in source
    assert "ownership_gaps" in source
    assert "migration-managed relation, function and custom type" in source
    assert "missing_schema_create" in source
    assert "prepare_production_migration_role" in source
    assert "validate_production_migration_role" in source
