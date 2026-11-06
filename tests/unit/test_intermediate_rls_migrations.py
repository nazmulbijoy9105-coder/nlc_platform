from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_webhook_reconciliation_is_fail_closed_before_signed_identity():
    migration = (
        ROOT / "alembic" / "versions" / "0044_webhook_schema_reconcile.py"
    ).read_text(encoding="utf-8")

    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "DROP POLICY" in migration
    assert "current_setting('app.current_user_id'" not in migration
    assert "CREATE POLICY" not in migration
    assert "CREATE TABLE IF NOT EXISTS" not in migration
    for table in ("webhook_endpoints", "webhook_deliveries", "rescue_audit_log"):
        assert f"to_regclass('public.{table}')" in migration
    assert "CREATE TABLE IF NOT EXISTS" not in migration
    assert "REQUIRED_TABLES" in migration
    assert "will not recreate empty tables" in migration


def test_rescue_audit_table_is_forced_rls_when_created():
    migration = (
        ROOT / "alembic" / "versions" / "0038_add_rescue_audit_log.py"
    ).read_text(encoding="utf-8")

    create_table = migration.index('op.create_table(\n        "rescue_audit_log"')
    force_rls = migration.index(
        "ALTER TABLE public.rescue_audit_log FORCE ROW LEVEL SECURITY"
    )
    assert force_rls > create_table
    assert "REVOKE ALL ON TABLE public.rescue_audit_log FROM PUBLIC" in migration


def test_webhook_tables_are_forced_rls_when_created():
    migration = (
        ROOT / "alembic" / "versions" / "0037_add_webhook_tables.py"
    ).read_text(encoding="utf-8")

    for table in ("webhook_endpoints", "webhook_deliveries"):
        assert f"ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in migration
        assert f"ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY" in migration
        assert f"REVOKE ALL ON TABLE public.{table} FROM PUBLIC" in migration
