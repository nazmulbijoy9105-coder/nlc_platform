"""
app/services/webhook_service.py — Webhook delivery engine.

Triggers HMAC-signed webhook deliveries when compliance events occur.
Includes exponential backoff retry (3 attempts), response logging,
and batch delivery for efficiency.

Integration: Call WebhookService.trigger_event() from compliance_service,
rescue_service, and deadline checker tasks.
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Any
from uuid import UUID

import httpx
import structlog
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import (
    WebhookEndpoint, WebhookDelivery,
    WebhookEvent, DeliveryStatus,
)

logger = structlog.get_logger(__name__)

# Retry config
MAX_ATTEMPTS = 3
INITIAL_RETRY_DELAY = 2  # seconds
REQUEST_TIMEOUT = 10.0  # seconds


def sign_payload(payload: dict, secret: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    body = json.dumps(payload, sort_keys=True, default=str)
    return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()


def verify_signature(payload: dict, secret: str, signature: str) -> bool:
    """Verify a webhook signature (for customers to verify on their end)."""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


class WebhookService:
    """Manages webhook endpoints, event triggering, and delivery."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Endpoint Management ──────────────────────────────────────

    async def register_endpoint(
        self, user_id: UUID, url: str, events: list[str] | None = None
    ) -> WebhookEndpoint:
        """Register a new webhook endpoint. Secret is auto-generated."""
        import secrets
        endpoint = WebhookEndpoint(
            user_id=user_id,
            url=url,
            secret=secrets.token_urlsafe(32),
            events=events or [],  # Empty = subscribe to ALL events
            is_active=True,
        )
        self.db.add(endpoint)
        await self.db.flush()
        logger.info("webhook_registered", endpoint_id=str(endpoint.id), url=url, events=events)
        return endpoint

    async def list_endpoints(self, user_id: UUID) -> list[WebhookEndpoint]:
        """List all webhook endpoints for a user."""
        result = await self.db.execute(
            select(WebhookEndpoint)
            .where(WebhookEndpoint.user_id == user_id)
            .order_by(WebhookEndpoint.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_endpoint(
        self, endpoint_id: UUID, url: str | None = None,
        events: list[str] | None = None, is_active: bool | None = None
    ) -> WebhookEndpoint | None:
        """Update a webhook endpoint."""
        endpoint = await self.db.get(WebhookEndpoint, endpoint_id)
        if not endpoint:
            return None
        if url is not None:
            endpoint.url = url
        if events is not None:
            endpoint.events = events
        if is_active is not None:
            endpoint.is_active = is_active
        self.db.add(endpoint)
        await self.db.flush()
        return endpoint

    async def delete_endpoint(self, endpoint_id: UUID) -> bool:
        """Delete a webhook endpoint."""
        endpoint = await self.db.get(WebhookEndpoint, endpoint_id)
        if not endpoint:
            return False
        await self.db.delete(endpoint)
        await self.db.flush()
        return True

    async def rotate_secret(self, endpoint_id: UUID) -> str | None:
        """Generate a new signing secret (for security rotation)."""
        import secrets
        endpoint = await self.db.get(WebhookEndpoint, endpoint_id)
        if not endpoint:
            return None
        endpoint.secret = secrets.token_urlsafe(32)
        self.db.add(endpoint)
        await self.db.flush()
        return endpoint.secret

    # ── Event Triggering ────────────────────────────────────────

    async def trigger_event(
        self, event_type: str, payload: dict, user_id: UUID | None = None
    ) -> int:
        """
        Trigger a webhook event. Finds all matching active endpoints,
        creates delivery records, and attempts immediate delivery.

        Returns: number of deliveries queued.
        """
        # Find matching endpoints
        query = select(WebhookEndpoint).where(
            WebhookEndpoint.is_active == True,  # noqa: E712
        )
        result = await self.db.execute(query)
        endpoints = list(result.scalars().all())

        # Filter by event subscription (empty events = subscribe to ALL)
        matching = [
            ep for ep in endpoints
            if not ep.events or event_type in ep.events
        ]

        # Also filter by user_id if provided (tenant isolation)
        if user_id:
            matching = [ep for ep in matching if ep.user_id == user_id]

        count = 0
        for endpoint in matching:
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=event_type,
                payload={
                    **payload,
                    "event_type": event_type,
                    "timestamp": datetime.now(UTC).isoformat(),
                },
                status=DeliveryStatus.PENDING,
                max_attempts=MAX_ATTEMPTS,
            )
            self.db.add(delivery)
            count += 1

        await self.db.flush()

        # Attempt immediate delivery (non-blocking)
        if matching:
            asyncio.create_task(self._deliver_pending())

        logger.info("webhook_triggered", event_type=event_type, endpoints=count)
        return count

    # ── Delivery Engine ─────────────────────────────────────────

    async def _deliver_pending(self) -> None:
        """Find pending deliveries and attempt to deliver them."""
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.status == DeliveryStatus.PENDING)
            .order_by(WebhookDelivery.created_at)
            .limit(50)
        )
        deliveries = list(result.scalars().all())

        for delivery in deliveries:
            await self._attempt_delivery(delivery)

    async def _attempt_delivery(self, delivery: WebhookDelivery) -> None:
        """Attempt to deliver a single webhook. Retries on failure."""
        endpoint = await self.db.get(WebhookEndpoint, delivery.endpoint_id)
        if not endpoint or not endpoint.is_active:
            delivery.status = DeliveryStatus.FAILED
            delivery.error_message = "Endpoint deleted or inactive"
            self.db.add(delivery)
            await self.db.flush()
            return

        delivery.attempts += 1
        headers = {
            "Content-Type": "application/json",
            "X-NLC-Event": delivery.event_type,
            "X-NLC-Delivery": str(delivery.id),
            "X-NLC-Signature": sign_payload(delivery.payload, endpoint.secret),
            "X-NLC-Timestamp": datetime.now(UTC).isoformat(),
        }

        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
                resp = await client.post(endpoint.url, json=delivery.payload, headers=headers)

            delivery.response_code = resp.status_code
            delivery.response_body = resp.text[:1000]  # Truncate for storage

            if resp.status_code < 300:
                delivery.status = DeliveryStatus.DELIVERED
                delivery.delivered_at = datetime.now(UTC)
                delivery.next_retry_at = None
                logger.info("webhook_delivered",
                    delivery_id=str(delivery.id),
                    endpoint=endpoint.url[:50],
                    status_code=resp.status_code)
            else:
                # Non-2xx response — retry if attempts remain
                if delivery.attempts >= delivery.max_attempts:
                    delivery.status = DeliveryStatus.FAILED
                    delivery.error_message = f"HTTP {resp.status_code} after {delivery.attempts} attempts"
                else:
                    delay = INITIAL_RETRY_DELAY * (2 ** (delivery.attempts - 1))
                    delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
                    delivery.error_message = f"HTTP {resp.status_code}, will retry"
                logger.warning("webhook_delivery_failed",
                    delivery_id=str(delivery.id),
                    status_code=resp.status_code,
                    attempts=delivery.attempts)

        except Exception as e:
            delivery.error_message = str(e)[:500]
            if delivery.attempts >= delivery.max_attempts:
                delivery.status = DeliveryStatus.FAILED
            else:
                delay = INITIAL_RETRY_DELAY * (2 ** (delivery.attempts - 1))
                delivery.next_retry_at = datetime.now(UTC) + timedelta(seconds=delay)
            logger.error("webhook_delivery_error",
                delivery_id=str(delivery.id),
                error=str(e),
                attempts=delivery.attempts)

        # Update endpoint's last delivery info
        endpoint.last_delivery_at = datetime.now(UTC)
        endpoint.last_response_code = delivery.response_code

        self.db.add(delivery)
        self.db.add(endpoint)
        await self.db.flush()

    async def process_retries(self) -> int:
        """Find deliveries scheduled for retry and attempt them again."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.status == DeliveryStatus.PENDING,
                WebhookDelivery.next_retry_at <= now,
            )
            .limit(50)
        )
        retries = list(result.scalars().all())

        for delivery in retries:
            await self._attempt_delivery(delivery)

        if retries:
            logger.info("webhook_retries_processed", count=len(retries))
        return len(retries)

    async def send_test_event(self, endpoint_id: UUID) -> dict:
        """Send a test event to verify webhook configuration."""
        test_payload = {
            "event_type": "webhook.test",
            "message": "This is a test webhook from Neum Lex Counsel",
            "timestamp": datetime.now(UTC).isoformat(),
        }
        endpoint = await self.db.get(WebhookEndpoint, endpoint_id)
        if not endpoint:
            return {"error": "Endpoint not found"}

        delivery = WebhookDelivery(
            endpoint_id=endpoint_id,
            event_type="webhook.test",
            payload=test_payload,
            status=DeliveryStatus.PENDING,
            max_attempts=1,
        )
        self.db.add(delivery)
        await self.db.flush()
        await self._attempt_delivery(delivery)

        return {
            "delivery_id": str(delivery.id),
            "status": delivery.status,
            "response_code": delivery.response_code,
            "response_body": delivery.response_body,
            "error": delivery.error_message,
        }

    # ── Delivery Log ────────────────────────────────────────────

    async def get_deliveries(
        self, endpoint_id: UUID, limit: int = 50
    ) -> list[WebhookDelivery]:
        """Get delivery history for an endpoint."""
        result = await self.db.execute(
            select(WebhookDelivery)
            .where(WebhookDelivery.endpoint_id == endpoint_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
