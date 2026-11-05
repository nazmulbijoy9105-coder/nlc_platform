"""Customer-facing legal alerts must obey the statutory release gate."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.rule_engine.engine as engine_module
from app.rule_engine.engine import RuleState
import app.services.notification_service as notification_module
from app.models.enums import NotificationStatus
from app.services.notification_service import NotificationService, is_notification_eligible


def _red_flag():
    return SimpleNamespace(
        rule_id="AGM-001",
        severity="RED",
        state=RuleState.NON_COMPLIANT,
        eval_state="VIOLATION",
        description="Test-only provisional finding",
        statutory_basis="Test-only basis",
        score_impact=15,
        revenue_tier="COMPLIANCE_PACKAGE",
    )


@pytest.mark.asyncio
async def test_provisional_red_flag_is_not_notified_before_legal_release(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    service = NotificationService(MagicMock())
    service.queue_notification = AsyncMock()

    await service.queue_for_new_flags(uuid4(), [_red_flag()])

    service.queue_notification.assert_not_awaited()


@pytest.mark.asyncio
async def test_unapproved_rule_is_not_notified_even_if_release_switch_is_true(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset())
    service = NotificationService(MagicMock())
    service.queue_notification = AsyncMock()

    await service.queue_for_new_flags(uuid4(), [_red_flag()])

    service.queue_notification.assert_not_awaited()


@pytest.mark.asyncio
async def test_released_approved_red_flag_queues_dashboard_alert(monkeypatch):
    monkeypatch.setattr(engine_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(engine_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    service = NotificationService(MagicMock())
    service.queue_notification = AsyncMock()

    await service.queue_for_new_flags(uuid4(), [_red_flag()])

    service.queue_notification.assert_awaited_once()
    assert service.queue_notification.await_args.kwargs["notification_type"] == "AGM-001"

def test_unreleased_rule_notifications_are_not_eligible(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    monkeypatch.setattr(notification_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))

    assert is_notification_eligible("PAYMENT_RECEIVED") is True
    assert is_notification_eligible("AGM-001") is False
    assert is_notification_eligible("TAX-001") is False


def test_only_approved_rule_notifications_are_eligible_after_release(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(notification_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))

    assert is_notification_eligible("PAYMENT_RECEIVED") is True
    assert is_notification_eligible("AGM-001") is True
    assert is_notification_eligible("TAX-001") is False


@pytest.mark.asyncio
async def test_mark_suppressed_persists_terminal_status():
    notification = SimpleNamespace(id=uuid4())
    service = NotificationService(MagicMock())
    service.get_by_id = AsyncMock(return_value=notification)
    service.update_instance = AsyncMock(return_value=notification)

    await service.mark_suppressed(notification.id, "awaiting legal approval")

    service.update_instance.assert_awaited_once_with(
        notification,
        notification_status=NotificationStatus.SUPPRESSED,
        failure_reason="awaiting legal approval",
    )

