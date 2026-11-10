"""Fail-closed notification delivery policy for legal and statutory alerts."""

import pytest

from app.services.notification_service import is_notification_eligible


@pytest.mark.parametrize(
    "notification_type",
    [
        "AGM_DEADLINE_WARNING",
        "DEADLINE_AGM",
        "CORPORATE_TAX_RETURN_DEADLINE_WARNING",
        "VAT_RETURN_DEADLINE_WARNING",
        "BSEC_Q1_REPORT_DEADLINE_WARNING",
        "LABOUR_LICENCE_DEADLINE_WARNING",
        "TRADE_LICENSE_DEADLINE_WARNING",
        "COMPLIANCE_ALERT",
        "LEGAL_ALERT",
        "RISK_ALERT",
        "TAX_RETURN_OVERDUE",
        "BILLING_TAX_RETURN_DEADLINE_WARNING",
        "VAT_RETURN_OVERDUE",
        "UNKNOWN_LEGAL_TYPE",
        "SRO_RULE_UPDATE_REQUIRED",
        "ARBITRARY_UNREGISTERED_TYPE",
    ],
)
def test_legal_deadline_and_unknown_notifications_are_suppressed(notification_type):
    assert is_notification_eligible(notification_type) is False


@pytest.mark.parametrize(
    "notification_type",
    [
        "SYSTEM",
        "AI_REVIEW_QUEUE_ALERT",
        "PAYMENT_RECEIPT",
        "BILLING_INVOICE",
        "BILLING_DEADLINE_WARNING",
        "PAYMENT_DEADLINE_WARNING",
        "SUBSCRIPTION_RENEWED",
        "ACCOUNT_SECURITY_LOGIN_ALERT",
    ],
)
def test_known_non_legal_operational_notifications_remain_eligible(notification_type):
    assert is_notification_eligible(notification_type) is True


def test_product_allowlisted_rule_notifications_are_eligible_while_legal_review_is_pending():
    assert is_notification_eligible("AGM-001") is True
    assert is_notification_eligible("VAT-002") is True


def test_any_notification_linked_to_a_compliance_flag_is_suppressed():
    from uuid import uuid4

    assert is_notification_eligible("SYSTEM", related_flag_id=uuid4()) is False

def test_deadline_worker_withholds_global_scan_until_calendar_release(monkeypatch):
    import app.services.compliance_calendar as calendar_module
    import app.worker.tasks.core as worker_core

    monkeypatch.setattr(calendar_module, "LEGAL_CALENDAR_RELEASED", False)
    monkeypatch.setattr(calendar_module, "VERIFIED_CALENDAR_EVENT_TYPES", frozenset())
    monkeypatch.setattr(
        worker_core,
        "run_async",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("worker must not open a privileged global scan")
        ),
    )

    result = worker_core.queue_deadline_warning_notifications.run(warning_days=[30])

    assert result == {
        "queued": 0,
        "deadlines_checked": 0,
        "status": "WITHHELD_LEGAL_CALENDAR_NOT_RELEASED",
    }


def test_deadline_worker_rejects_invalid_warning_thresholds():
    import app.worker.tasks.core as worker_core

    with pytest.raises(ValueError, match="non-negative"):
        worker_core.queue_deadline_warning_notifications.run(warning_days=[30, -1])
