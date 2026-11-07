from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_revenue_pipeline_uses_verified_invoice_allocations():
    migration = (
        ROOT / "alembic" / "versions" / "0066_verified_revenue_pipeline.py"
    ).read_text(encoding="utf-8")

    assert "public.invoices" in migration
    assert "public.payment_allocations" in migration
    assert "public.payments" in migration
    assert "p.status = 'SETTLED'" in migration
    assert "status NOT IN ('DRAFT', 'VOID')" in migration
    assert "e.invoiced_bdt" not in migration
    assert "e.collected_bdt" not in migration


def test_manual_payment_reference_migration_preflights_duplicates_and_adds_unique_indexes():
    migration = (
        ROOT / "alembic" / "versions" / "0067_unique_manual_wallet_references.py"
    ).read_text(encoding="utf-8")

    assert "payment_submissions" in migration
    assert "public.payments" in migration
    assert "lower(btrim(payer_reference))" in migration
    assert "status <> 'REJECTED'" not in migration
    model = (ROOT / "app" / "models" / "finance.py").read_text(encoding="utf-8")
    assert "payer_reference IS NOT NULL AND method IN ('BANK_TRANSFER','CHEQUE') AND status <> 'REJECTED'" not in model
    assert "CREATE UNIQUE INDEX uq_payment_submission_manual_reference" in migration
    assert "CREATE UNIQUE INDEX uq_payment_manual_reference" in migration
    assert "ck_payment_submission_reference_required" in migration
    assert "ck_payment_reference_required" in migration


def test_forward_repair_enforces_invoker_views_and_admin_only_revenue_rls():
    migration = (
        ROOT / "alembic" / "versions"
        / "0068_repair_aggregate_view_and_revenue_rls.py"
    ).read_text(encoding="utf-8")

    assert 'down_revision = "0067_unique_manual_wallet_references"' in migration
    assert "security_invoker = true" in migration
    assert "nlc_current_user_is_revenue_staff" in migration
    assert "engagements_revenue_staff_only" in migration
    assert "nlc_can_view_billing_company" in migration
    assert "nlc_can_submit_payment_company" in migration
    assert migration.count("NOT public.nlc_current_user_is_staff()") >= 3
    assert "can_view_financials IS TRUE" in migration
    assert "can_edit IS TRUE" in migration
    assert "FORCE ROW LEVEL SECURITY" in migration


def test_legal_staff_quotation_regression_uses_privileged_membership():
    integration = (
        ROOT / "tests" / "integration" / "test_rls_hardening.py"
    ).read_text(encoding="utf-8")
    start = integration.index(
        "async def test_legal_staff_cannot_read_engagements_quotations_or_revenue_pipeline"
    )
    test_body = integration[start:]
    assert "can_edit=True" in test_body
    assert "can_view_financials=True" in test_body
    assert "view_only_user" in test_body
    assert "can_view_financials=False" in test_body
