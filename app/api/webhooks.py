"""
app/api/webhooks.py — Webhook management API.

Endpoints:
  POST   /webhooks              Register a webhook endpoint
  GET    /webhooks              List user's webhook endpoints
  PATCH  /webhooks/{id}         Update endpoint (URL, events, active)
  DELETE /webhooks/{id}         Delete endpoint
  POST   /webhooks/{id}/test    Send a test event
  GET    /webhooks/{id}/deliveries  Get delivery history
  GET    /webhooks/events       List available event types

All endpoints require ADMIN_STAFF or SUPER_ADMIN role.
"""
from __future__ import annotations

import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db_for_user, get_current_user
from app.models.user import User
from app.models.webhook import WebhookEvent
from app.services.webhook_service import WebhookService

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────

class WebhookCreateRequest(BaseModel):
    url: HttpUrl = Field(..., description="HTTPS URL to receive webhook POST")
    events: List[str] = Field(
        default=[], description="Event types to subscribe to. Empty = all events."
    )


class WebhookUpdateRequest(BaseModel):
    url: HttpUrl | None = None
    events: List[str] | None = None
    is_active: bool | None = None


class WebhookResponse(BaseModel):
    id: str
    url: str
    secret: str  # Only shown once on creation/update
    events: List[str]
    is_active: bool
    last_delivery_at: str | None = None
    last_response_code: int | None = None
    created_at: str


class DeliveryResponse(BaseModel):
    id: str
    event_type: str
    status: str
    attempts: int
    response_code: int | None
    error_message: str | None
    delivered_at: str | None
    created_at: str


class TestResponse(BaseModel):
    delivery_id: str
    status: str
    response_code: int | None
    response_body: str | None
    error: str | None = None


# ── Routes ───────────────────────────────────────────────────────

@router.get("/events", summary="List available webhook event types")
async def list_events():
    """Returns all webhook event types customers can subscribe to."""
    return {"events": WebhookEvent.ALL_EVENTS}


@router.post("", response_model=WebhookResponse, summary="Register a webhook endpoint")
async def create_webhook(
    body: WebhookCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Register a new webhook URL to receive compliance event notifications."""
    svc = WebhookService(db)
    endpoint = await svc.register_endpoint(
        user_id=current_user.id,
        url=str(body.url),
        events=body.events,
    )
    await db.commit()
    return WebhookResponse(
        id=str(endpoint.id),
        url=endpoint.url,
        secret=endpoint.secret,
        events=endpoint.events,
        is_active=endpoint.is_active,
        last_delivery_at=endpoint.last_delivery_at.isoformat() if endpoint.last_delivery_at else None,
        last_response_code=endpoint.last_response_code,
        created_at=endpoint.created_at.isoformat() if endpoint.created_at else "",
    )


@router.get("", response_model=List[WebhookResponse], summary="List webhook endpoints")
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """List all webhook endpoints for the current user."""
    svc = WebhookService(db)
    endpoints = await svc.list_endpoints(current_user.id)
    return [
        WebhookResponse(
            id=str(ep.id),
            url=ep.url,
            secret="***",  # Don't expose secret on list
            events=ep.events,
            is_active=ep.is_active,
            last_delivery_at=ep.last_delivery_at.isoformat() if ep.last_delivery_at else None,
            last_response_code=ep.last_response_code,
            created_at=ep.created_at.isoformat() if ep.created_at else "",
        )
        for ep in endpoints
    ]


@router.patch("/{endpoint_id}", response_model=WebhookResponse, summary="Update webhook endpoint")
async def update_webhook(
    endpoint_id: uuid.UUID,
    body: WebhookUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Update webhook URL, events, or active status."""
    svc = WebhookService(db)
    endpoint = await svc.update_endpoint(
        endpoint_id=endpoint_id,
        url=str(body.url) if body.url else None,
        events=body.events,
        is_active=body.is_active,
    )
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await db.commit()
    return WebhookResponse(
        id=str(endpoint.id),
        url=endpoint.url,
        secret=endpoint.secret,
        events=endpoint.events,
        is_active=endpoint.is_active,
        last_delivery_at=endpoint.last_delivery_at.isoformat() if endpoint.last_delivery_at else None,
        last_response_code=endpoint.last_response_code,
        created_at=endpoint.created_at.isoformat() if endpoint.created_at else "",
    )


@router.delete("/{endpoint_id}", summary="Delete webhook endpoint")
async def delete_webhook(
    endpoint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Delete a webhook endpoint."""
    svc = WebhookService(db)
    deleted = await svc.delete_endpoint(endpoint_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    await db.commit()
    return {"message": "Webhook endpoint deleted"}


@router.post("/{endpoint_id}/test", response_model=TestResponse, summary="Send test event")
async def test_webhook(
    endpoint_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Send a test event to verify the webhook is working."""
    svc = WebhookService(db)
    result = await svc.send_test_event(endpoint_id)
    await db.commit()
    return TestResponse(**result)


@router.get("/{endpoint_id}/deliveries", response_model=List[DeliveryResponse], summary="Get delivery history")
async def get_deliveries(
    endpoint_id: uuid.UUID,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    """Get delivery history for a webhook endpoint."""
    svc = WebhookService(db)
    deliveries = await svc.get_deliveries(endpoint_id, limit=limit)
    return [
        DeliveryResponse(
            id=str(d.id),
            event_type=d.event_type,
            status=d.status,
            attempts=d.attempts,
            response_code=d.response_code,
            error_message=d.error_message,
            delivered_at=d.delivered_at.isoformat() if d.delivered_at else None,
            created_at=d.created_at.isoformat() if d.created_at else "",
        )
        for d in deliveries
    ]
