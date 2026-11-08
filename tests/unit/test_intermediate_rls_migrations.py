from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_webhook_reconciliation_reconstructs_schema_but_stays_fail_closed():
    migration = (
        ROOT / "alembic" / "versions" / "0044_webhook_schema_reconcile.py"
    ).read_text(encoding="utf-8")

    assert "_create_missing_tables()" in migration
    assert "op.create_table(" in migration
    assert "SCHEMA-ONLY RECONSTRUCTION" in migration
    assert "historical endpoint rows were not restored" in migration
    assert "historical delivery and retry rows were not restored" in migration
    assert "Historical rescue audit rows were not restored" in migration
    assert "ENABLE ROW LEVEL SECURITY" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration
    assert "DROP POLICY" in migration
    assert "current_setting('app.current_user_id'" not in migration
    assert "CREATE POLICY" not in migration


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

    assert 'for table in ("webhook_endpoints", "webhook_deliveries")' in migration
    assert "ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY" in migration
    assert "ALTER TABLE public.{table} FORCE ROW LEVEL SECURITY" in migration
    assert "REVOKE ALL ON TABLE public.{table} FROM PUBLIC" in migration
