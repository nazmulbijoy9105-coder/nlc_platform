"""Regression checks for tenant-scoped payment references and timestamps."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import ForeignKeyConstraint, UniqueConstraint

from app.api.finance import (
    CUSTOMER_BILLING_READ_ROLES,
    CUSTOMER_BILLING_WRITE_ROLES,
    OfflinePaymentSubmissionRequest,
    PaymentApprovalRequest,
)
from app.models.finance import Payment, PaymentSubmission


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


def test_offline_payment_timestamp_requires_explicit_timezone():
    with pytest.raises(ValidationError, match="paid_at must include an explicit timezone offset"):
        OfflinePaymentSubmissionRequest(
            invoice_id=uuid4(),
            method="CASH",
            amount_bdt=Decimal("10.00"),
            paid_at=datetime(2026, 11, 6, 12, 0, 0),
        )

    accepted = OfflinePaymentSubmissionRequest(
        invoice_id=uuid4(),
        method="CASH",
        amount_bdt=Decimal("10.00"),
        paid_at=datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    assert accepted.paid_at is not None
    assert accepted.paid_at.utcoffset() is not None


def test_cheque_clearance_timestamp_requires_explicit_timezone():
    with pytest.raises(
        ValidationError,
        match="cheque_cleared_at must include an explicit timezone offset",
    ):
        PaymentApprovalRequest(
            cheque_cleared_at=datetime(2026, 11, 6, 12, 0, 0)
        )

    accepted = PaymentApprovalRequest(
        cheque_cleared_at=datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc)
    )
    assert accepted.cheque_cleared_at is not None
    assert accepted.cheque_cleared_at.utcoffset() is not None


def test_finance_service_rejects_naive_timestamps_even_when_called_directly():
    from app.services.finance_service import (
        FinanceConflictError,
        _require_aware_datetime,
    )

    with pytest.raises(FinanceConflictError, match="paid_at must include an explicit timezone offset"):
        _require_aware_datetime(datetime(2026, 11, 6, 12, 0, 0), "paid_at")

    _require_aware_datetime(
        datetime(2026, 11, 6, 12, 0, 0, tzinfo=timezone.utc),
        "paid_at",
    )


def test_billing_permissions_match_defined_client_roles():
    assert {"CLIENT_DIRECTOR", "CLIENT_VIEW_ONLY"} <= set(CUSTOMER_BILLING_READ_ROLES)
    assert "CLIENT_DIRECTOR" in CUSTOMER_BILLING_WRITE_ROLES
    assert "CLIENT_VIEW_ONLY" not in CUSTOMER_BILLING_WRITE_ROLES
    assert "CLIENT" not in CUSTOMER_BILLING_READ_ROLES


def test_manual_payment_reference_indexes_exist_on_claims_and_receipts():
    submission_indexes = {index.name for index in PaymentSubmission.__table__.indexes}
    payment_indexes = {index.name for index in Payment.__table__.indexes}

    assert "uq_payment_submission_manual_reference" in submission_indexes
    assert "uq_payment_manual_reference" in payment_indexes
