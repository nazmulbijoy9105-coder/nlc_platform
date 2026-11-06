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
