"""
NEUM LEX COUNSEL — Notifications API
app/api/notifications.py

Routes:
  GET    /notifications/                  — current user's notifications
  POST   /notifications/{id}/acknowledge  — mark acknowledged
  GET    /notifications/pending           — admin/Celery pending queue
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db_for_user, require_admin
from app.models.enums import NotificationChannel
from app.services.notification_service import NotificationService

router = APIRouter()


def _get_svc(db: AsyncSession = Depends(get_db_for_user)) -> NotificationService:
    return NotificationService(db)


@router.get("/")
async def get_my_notifications(
    company_id: uuid.UUID | None = Query(None),
    unread_only: bool = Query(False),
    limit: int = Query(50, le=200),
    current_user=Depends(get_current_user),
    svc: NotificationService = Depends(_get_svc),
):
    notifications = await svc.get_for_user(
        current_user.id,
        company_id=company_id,
        unread_only=unread_only,
        limit=limit,
    )
    return [
        {
            "id":                  str(n.id),
            "company_id":          str(n.company_id) if n.company_id else None,
            "title":               n.title,
            "body":                n.body,
            "notification_type":   n.notification_type,
            "channel":             n.channel.value,
            "status":              n.notification_status.value,
            "days_until_deadline": n.days_until_deadline,
            "related_flag_id":     str(n.related_flag_id) if n.related_flag_id else None,
            "scheduled_for":       n.scheduled_for.isoformat() if n.scheduled_for else None,
            "sent_at":             n.sent_at.isoformat() if n.sent_at else None,
            "acknowledged_at":     n.acknowledged_at.isoformat() if n.acknowledged_at else None,
            "created_at":          n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]


@router.post("/{notification_id}/acknowledge")
async def acknowledge_notification(
    notification_id: uuid.UUID,
    current_user=Depends(get_current_user),
    svc: NotificationService = Depends(_get_svc),
):
    notif = await svc.get_by_id(notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    if notif.user_id and notif.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your notification")
    updated = await svc.acknowledge(notification_id, current_user.id)
    if not updated:
        raise HTTPException(status_code=404, detail="Notification not found")
    await svc.db.commit()
    return {"id": str(updated.id), "status": updated.notification_status.value}


@router.get("/pending")
async def get_pending_notifications(
    channel: NotificationChannel | None = Query(None),
    limit: int = Query(100, le=500),
    _=Depends(require_admin()),
    svc: NotificationService = Depends(_get_svc),
):
    notifications = await svc.get_pending(channel=channel, limit=limit)
    return [
        {
            "id":                str(n.id),
            "company_id":        str(n.company_id) if n.company_id else None,
            "user_id":           str(n.user_id) if n.user_id else None,
            "title":             n.title,
            "body":              n.body,
            "notification_type": n.notification_type,
            "channel":           n.channel.value,
            "retry_count":       n.retry_count,
            "scheduled_for":     n.scheduled_for.isoformat() if n.scheduled_for else None,
            "created_at":        n.created_at.isoformat() if n.created_at else None,
        }
        for n in notifications
    ]
