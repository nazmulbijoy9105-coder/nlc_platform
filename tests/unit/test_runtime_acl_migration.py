from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_runtime_acl_migration_preserves_only_required_delete_workflows():
    source = (
        ROOT
        / "alembic"
        / "versions"
        / "0112_runtime_acl_and_alembic_rls.py"
    ).read_text(encoding="utf-8")

    assert 'REVOKE DELETE ON ALL TABLES IN SCHEMA public FROM nlc_app_role' in source
    assert 'GRANT DELETE ON TABLE public.webhook_endpoints TO nlc_app_role' in source
    assert 'GRANT DELETE ON TABLE public.user_activity_logs TO nlc_app_role' in source
    assert 'ALTER TABLE public.alembic_version FORCE ROW LEVEL SECURITY' in source

    for view in (
        "vw_admin_dashboard_kpis",
        "vw_company_flag_summary",
        "vw_risk_distribution",
        "vw_upcoming_deadlines",
        "vw_revenue_pipeline",
    ):
        assert view in source
        assert "REVOKE INSERT, UPDATE, DELETE ON TABLE public." in source


def test_runtime_acl_migration_is_forward_only():
    source = (
        ROOT
        / "alembic"
        / "versions"
        / "0112_runtime_acl_and_alembic_rls.py"
    ).read_text(encoding="utf-8")

    downgrade = source.split("def downgrade() -> None:", 1)[1]
    assert "pass" in downgrade
