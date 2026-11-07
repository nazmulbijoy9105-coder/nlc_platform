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
        "VAT_RETURN_OVERDUE",
        "UNKNOWN_LEGAL_TYPE",
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
        "SRO_RULE_UPDATE_REQUIRED",
        "PAYMENT_RECEIPT",
        "BILLING_INVOICE",
        "SUBSCRIPTION_RENEWED",
        "ACCOUNT_SECURITY_LOGIN_ALERT",
    ],
)
def test_known_non_legal_operational_notifications_remain_eligible(notification_type):
    assert is_notification_eligible(notification_type) is True


def test_rule_id_notifications_remain_suppressed_until_legal_release():
    assert is_notification_eligible("AGM-001") is False
    assert is_notification_eligible("VAT-002") is False


def test_any_notification_linked_to_a_compliance_flag_is_suppressed():
    from uuid import uuid4

    assert is_notification_eligible("SYSTEM", related_flag_id=uuid4()) is False
