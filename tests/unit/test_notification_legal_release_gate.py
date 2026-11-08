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

@pytest.mark.asyncio
async def test_user_notification_list_hides_unapproved_rule_alerts(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    legal_alert = SimpleNamespace(notification_type="TAX-001", notification_status=NotificationStatus.PENDING)
    payment_notice = SimpleNamespace(notification_type="PAYMENT_RECEIVED", notification_status=NotificationStatus.PENDING)
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [legal_alert, payment_notice])
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    service = NotificationService(db)

    visible = await service.get_for_user(uuid4())

    assert visible == [payment_notice]

@pytest.mark.asyncio
async def test_suppressed_rule_notifications_stay_hidden_after_release(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(notification_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))
    suppressed = SimpleNamespace(
        notification_type="AGM-001",
        notification_status=NotificationStatus.SUPPRESSED,
    )
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [suppressed])
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    service = NotificationService(db)

    visible = await service.get_for_user(uuid4())

    assert visible == []

@pytest.mark.asyncio
async def test_queue_notification_stores_unapproved_rule_alert_as_suppressed(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    service = NotificationService(MagicMock())
    service.create = AsyncMock(return_value=SimpleNamespace())

    await service.queue_notification(
        title="Provisional legal alert",
        body="Pending counsel review",
        notification_type="AGM-001",
    )

    kwargs = service.create.await_args.kwargs
    assert kwargs["notification_status"] == NotificationStatus.SUPPRESSED
    assert "not counsel-approved" in kwargs["failure_reason"]


@pytest.mark.asyncio
async def test_company_notification_list_hides_unapproved_rule_alerts(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    legal_alert = SimpleNamespace(
        notification_type="AGM-001",
        notification_status=NotificationStatus.PENDING,
    )
    payment_notice = SimpleNamespace(
        notification_type="PAYMENT_RECEIVED",
        notification_status=NotificationStatus.PENDING,
    )
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [legal_alert, payment_notice])
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    service = NotificationService(db)

    visible = await service.get_for_company(uuid4())

    assert visible == [payment_notice]



@pytest.mark.asyncio
async def test_pending_worker_queue_rechecks_release_gate_for_legacy_rows(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    legacy_legal_alert = SimpleNamespace(
        notification_type="AGM-001",
        related_flag_id=None,
    )
    payment_notice = SimpleNamespace(
        notification_type="PAYMENT_RECEIVED",
        related_flag_id=None,
    )
    result = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [legacy_legal_alert, payment_notice])
    )
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)
    service = NotificationService(db)

    pending = await service.get_pending()

    assert pending == [payment_notice]


@pytest.mark.asyncio
async def test_flag_linked_generic_notification_fails_closed(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    service = NotificationService(MagicMock())
    service.create = AsyncMock(return_value=SimpleNamespace())

    await service.queue_notification(
        title="Compliance alert",
        body="Provisional finding",
        notification_type="COMPLIANCE_FLAG",
        related_flag_id=uuid4(),
    )

    kwargs = service.create.await_args.kwargs
    assert kwargs["notification_status"] == NotificationStatus.SUPPRESSED


@pytest.mark.asyncio
async def test_generic_legal_alert_is_suppressed_even_without_flag_link(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", False)
    service = NotificationService(MagicMock())
    service.create = AsyncMock(return_value=SimpleNamespace())

    await service.queue_notification(
        title="Legal alert",
        body="Potential compliance breach",
        notification_type="COMPLIANCE_ALERT",
    )

    kwargs = service.create.await_args.kwargs
    assert kwargs["notification_status"] == NotificationStatus.SUPPRESSED


def test_related_flag_notification_is_never_eligible_even_after_rule_release(monkeypatch):
    monkeypatch.setattr(notification_module, "LEGAL_SCORE_RELEASED", True)
    monkeypatch.setattr(notification_module, "VERIFIED_RULE_IDS", frozenset({"AGM-001"}))

    assert is_notification_eligible("CUSTOM_ALERT", related_flag_id=uuid4()) is False
