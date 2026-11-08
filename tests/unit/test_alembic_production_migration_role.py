"""Regression tests for the production Alembic migration-role boundary."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_production_role_preflight_is_opt_in_outside_render():
    source = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")
    helper = (ROOT / "app" / "db_url.py").read_text(encoding="utf-8")

    assert "is_render_runtime(os.environ)" in source
    assert "RENDER_SERVICE_ID" in helper
    assert "RENDER_INSTANCE_ID" in helper
    assert 'os.environ.get("ENVIRONMENT", "").strip().lower()' in source
    assert 'environment in {"prod", "production"}' in source
    assert 'os.environ.get("ENVIRONMENT", "production")' not in source


def test_production_role_preflight_rejects_runtime_role_and_checks_owner():
    source = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert 'if role_name == "nlc_app_role":' in source
    assert "r.rolbypassrls" in source
    assert "audit_table.relowner = r.oid" in source
    assert "does not own public.rescue_audit_log" in source
    assert "do not grant ownership to nlc_app_role" in source


def test_production_role_preflight_runs_before_any_alembic_migrations():
    source = (ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    preflight = source.index("await connection.run_sync(validate_production_migration_role)")
    migrations = source.index("await connection.run_sync(do_run_migrations)")

    assert preflight < migrations
