"""Regression checks for tenant-scoped payment submission references."""
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.models.finance import PaymentSubmission


def test_payment_submission_has_composite_tenant_key_for_ledger_reference():
    constraints = PaymentSubmission.__table__.constraints

    assert any(
        isinstance(constraint, UniqueConstraint)
        and constraint.name == "uq_payment_submissions_id_company"
        and tuple(column.name for column in constraint.columns) == ("id", "company_id")
        for constraint in constraints
    )


def test_payment_submission_invoice_reference_is_company_scoped():
    constraints = PaymentSubmission.__table__.constraints

    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and tuple(element.parent.name for element in constraint.elements) == ("invoice_id", "company_id")
        and tuple(element.target_fullname for element in constraint.elements)
        == ("invoices.id", "invoices.company_id")
        for constraint in constraints
    )


def test_customer_billing_allowlist_matches_actual_user_roles():
    from app.api.finance import CUSTOMER_BILLING_ROLES

    assert set(CUSTOMER_BILLING_ROLES) == {
        "CLIENT_DIRECTOR",
        "CLIENT_VIEW_ONLY",
        "ADMIN_STAFF",
        "SUPER_ADMIN",
    }


def test_payment_submission_and_intent_rls_accept_overdue_invoices():
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    migration = (
        root / "alembic" / "versions" / "0059_financial_billing_core.py"
    ).read_text(encoding="utf-8")

    for policy_name in (
        "payment_submissions_submit_insert",
        "payment_intents_submit_insert",
    ):
        start = migration.index(f"CREATE POLICY {policy_name}")
        end = migration.index('""")', start)
        policy_sql = migration[start:end]
        assert "IN ('ISSUED','PARTIALLY_PAID','OVERDUE')" in policy_sql
