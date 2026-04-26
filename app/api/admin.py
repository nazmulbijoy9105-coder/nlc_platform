"""
app/api/admin.py — Administration Router
NEUM LEX COUNSEL

All endpoints require ADMIN_STAFF or SUPER_ADMIN roles unless noted.

Endpoints:
  Users:
    GET   /admin/users                  List all NLC staff users
    POST  /admin/users                  Create a new user (SUPER_ADMIN only)
    GET   /admin/users/{user_id}        Get user detail
    PATCH /admin/users/{user_id}        Update user (role, active status)
    POST  /admin/users/{user_id}/company-access  Grant company access
    DELETE /admin/users/{user_id}/company-access/{company_id} Revoke access
    POST  /admin/users/{user_id}/reset-totp  Reset 2FA for a user

  Notifications:
    GET   /admin/notifications/user/{user_id}    Notifications for a user
    POST  /admin/notifications/acknowledge/{id}  Acknowledge a notification

  Activity Logs:
    GET   /admin/logs/company/{company_id}   Activity logs for a company
    GET   /admin/logs/user/{user_id}         Activity logs for a user
    GET   /admin/logs/recent                 Recent activity across platform

  Maintenance:
    POST  /admin/maintenance/backup          Trigger S3 backup
    POST  /admin/maintenance/evaluate-all    Trigger full portfolio evaluation
    GET   /admin/maintenance/worker-health   Celery worker health check
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pydantic import BaseModel, Field, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db_for_user,
    get_current_user,
    require_roles,
    Pagination,
)
from app.models.user import User
from app.models.enums import UserRole
from app.services.user_service import UserService
from app.services.notification_service import NotificationService, ActivityService

logger = structlog.get_logger(__name__)
router = APIRouter()

ADMIN_ROLES = ["ADMIN_STAFF", "SUPER_ADMIN"]
SUPER_ADMIN_ONLY = ["SUPER_ADMIN"]


# ---------------------------------------------------------------------------
# Schemas — Users
# ---------------------------------------------------------------------------

class UserCreateRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=255)
    role: UserRole
    password: str = Field(min_length=12, max_length=128)


class UserUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class CompanyAccessRequest(BaseModel):
    company_id: uuid.UUID
    access_level: str = Field(default="FULL", description="FULL | VIEW_ONLY")


class UserAdminResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    totp_enabled: bool
    last_login_at: Optional[str]
    failed_login_attempts: int
    is_locked: bool
    created_at: str


# ---------------------------------------------------------------------------
# Schemas — Notifications
# ---------------------------------------------------------------------------

class NotificationResponse(BaseModel):
    notification_id: str
    company_id: Optional[str]
    user_id: str
    channel: str
    message: str
    status: str
    is_acknowledged: bool
    created_at: str
    sent_at: Optional[str]


# ---------------------------------------------------------------------------
# Schemas — Activity Logs
# ---------------------------------------------------------------------------

class ActivityLogResponse(BaseModel):
    log_id: str
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    description: Optional[str]
    actor_user_id: Optional[str]
    ip_address: Optional[str]
    created_at: str


# ---------------------------------------------------------------------------
# Schemas — Maintenance
# ---------------------------------------------------------------------------

class MessageResponse(BaseModel):
    message: str
    success: bool = True


class WorkerHealthResponse(BaseModel):
    status: str
    active_workers: int
    active_tasks: int
    queued_tasks: Dict = {}
    broker_reachable: bool
    timestamp: str


# ---------------------------------------------------------------------------
# Serialisers
# ---------------------------------------------------------------------------

def _user_to_admin_response(user) -> UserAdminResponse:
    return UserAdminResponse(
        user_id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        totp_enabled=user.totp_enabled,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        failed_login_attempts=user.failed_login_attempts or 0,
        is_locked=bool(user.locked_until),
        created_at=user.created_at.isoformat(),
    )


# ===========================================================================
# USER MANAGEMENT
# ===========================================================================

@router.get(
    "/users",
    response_model=List[UserAdminResponse],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="List all NLC staff users",
)
async def list_users(
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    from sqlalchemy import select
    from app.models.user import User as UserModel

    query = select(UserModel)
    if role:
        query = query.where(UserModel.role == role)
    if is_active is not None:
        query = query.where(UserModel.is_active == is_active)

    result = await db.execute(query.order_by(UserModel.created_at.desc()))
    users = result.scalars().all()
    return [_user_to_admin_response(u) for u in users]


@router.post(
    "/users",
    response_model=UserAdminResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(*SUPER_ADMIN_ONLY))],
    summary="Create a new NLC staff user (Super Admin only)",
)
async def create_user(
    body: UserCreateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    activity = ActivityService(db)

    existing = await svc.get_by_email(body.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with email '{body.email}' already exists.",
        )

    user = await svc.create_user(
        email=body.email,
        full_name=body.full_name,
        role=body.role,
        plain_password=body.password,
        created_by=current_user.id,
    )

    await activity.log(
        action="USER_CREATED",
        resource_type="user",
        resource_id=str(user.id),
        description=f"User '{body.email}' created with role {body.role}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _user_to_admin_response(user)


@router.get(
    "/users/{user_id}",
    response_model=UserAdminResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Get a user by ID",
)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    user = await svc.get_by_id_or_404(user_id)
    return _user_to_admin_response(user)


@router.patch(
    "/users/{user_id}",
    response_model=UserAdminResponse,
    dependencies=[Depends(require_roles(*SUPER_ADMIN_ONLY))],
    summary="Update a user (Super Admin only)",
)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    activity = ActivityService(db)

    update_data = body.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update.")

    user = await svc.update_by_id(user_id, **update_data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    await activity.log(
        action="USER_UPDATED",
        resource_type="user",
        resource_id=str(user_id),
        description=f"User updated. Fields: {list(update_data.keys())}",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return _user_to_admin_response(user)


@router.post(
    "/users/{user_id}/company-access",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Grant a user access to a company",
)
async def grant_company_access(
    user_id: uuid.UUID,
    body: CompanyAccessRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    activity = ActivityService(db)

    can_edit = body.access_level.upper() == "FULL"
    await svc.grant_company_access(
        user_id=user_id,
        company_id=body.company_id,
        can_edit=can_edit,
        granted_by=current_user.id,
    )

    await activity.log(
        action="COMPANY_ACCESS_GRANTED",
        resource_type="user",
        resource_id=str(user_id),
        description=f"Company {body.company_id} access granted ({body.access_level})",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(message="Company access granted.")


@router.delete(
    "/users/{user_id}/company-access/{company_id}",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Revoke a user's access to a company",
)
async def revoke_company_access(
    user_id: uuid.UUID,
    company_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    await svc.revoke_company_access(user_id=user_id, company_id=company_id)
    return MessageResponse(message="Company access revoked.")


@router.post(
    "/users/{user_id}/unlock",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Unlock a locked-out account and reset failed login counter",
)
async def unlock_account(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import update
    from app.models.user import User as UserModel
    from datetime import timezone as _tz
    import datetime as _dt

    await db.execute(
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(failed_login_attempts=0, locked_until=None)
    )
    await db.commit()

    activity = ActivityService(db)
    await activity.log(
        action="ACCOUNT_UNLOCKED",
        resource_type="user",
        resource_id=str(user_id),
        description="Account manually unlocked by admin",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(message="Account unlocked and login counter reset.")


@router.post(
    "/users/{user_id}/reset-totp",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(*SUPER_ADMIN_ONLY))],
    summary="Reset 2FA for a user (forces them to re-set up on next login)",
)
async def reset_totp(
    user_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    from sqlalchemy import update
    from app.models.user import User as UserModel

    await db.execute(
        update(UserModel)
        .where(UserModel.id == user_id)
        .values(totp_enabled=False, totp_secret_encrypted=None)
    )
    await db.commit()

    activity = ActivityService(db)
    await activity.log(
        action="TOTP_RESET",
        resource_type="user",
        resource_id=str(user_id),
        description="TOTP reset by Super Admin",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(message="2FA reset. User must re-configure on next login.")


# ===========================================================================
# NOTIFICATIONS
# ===========================================================================

@router.get(
    "/notifications/user/{user_id}",
    response_model=List[NotificationResponse],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Get notifications for a specific user",
)
async def get_user_notifications(
    user_id: uuid.UUID,
    unread_only: bool = False,
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = NotificationService(db)
    notifications = await svc.get_for_user(
        user_id=user_id,
        unread_only=unread_only,
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    return [
        NotificationResponse(
            notification_id=str(n.id),
            company_id=str(n.company_id) if n.company_id else None,
            user_id=str(n.user_id),
            channel=n.channel,
            message=n.message,
            status=n.status,
            is_acknowledged=n.is_acknowledged,
            created_at=n.created_at.isoformat(),
            sent_at=n.sent_at.isoformat() if n.sent_at else None,
        )
        for n in notifications
    ]


@router.post(
    "/notifications/acknowledge/{notification_id}",
    response_model=MessageResponse,
    summary="Acknowledge a notification",
)
async def acknowledge_notification(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = NotificationService(db)
    await svc.acknowledge(notification_id=notification_id, user_id=current_user.id)
    return MessageResponse(message="Notification acknowledged.")


# ===========================================================================
# ACTIVITY LOGS
# ===========================================================================

@router.get(
    "/logs/company/{company_id}",
    response_model=List[ActivityLogResponse],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Activity logs for a company",
)
async def get_company_logs(
    company_id: uuid.UUID,
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ActivityService(db)
    logs = await svc.get_logs(
        resource_type="company",
        resource_id=str(company_id),
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    return [_log_to_response(l) for l in logs]


@router.get(
    "/logs/user/{user_id}",
    response_model=List[ActivityLogResponse],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Activity logs for a specific user",
)
async def get_user_logs(
    user_id: uuid.UUID,
    pagination: Pagination = Depends(),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ActivityService(db)
    logs = await svc.get_logs(
        actor_user_id=str(user_id),
        limit=pagination.page_size,
        offset=pagination.offset,
    )
    return [_log_to_response(l) for l in logs]


@router.get(
    "/logs/recent",
    response_model=List[ActivityLogResponse],
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Recent platform-wide activity",
)
async def get_recent_logs(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = ActivityService(db)
    logs = await svc.get_logs(limit=limit, offset=0)
    return [_log_to_response(l) for l in logs]


def _log_to_response(log) -> ActivityLogResponse:
    return ActivityLogResponse(
        log_id=str(log.id),
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        description=log.description,
        actor_user_id=str(log.actor_user_id) if log.actor_user_id else None,
        ip_address=log.ip_address,
        created_at=log.created_at.isoformat(),
    )


# ===========================================================================
# MAINTENANCE
# ===========================================================================

@router.post(
    "/maintenance/backup",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(*SUPER_ADMIN_ONLY))],
    summary="Trigger a manual activity log backup to S3",
)
async def trigger_backup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    activity = ActivityService(db)

    try:
        from app.worker.tasks import cleanup_old_activity_logs
        task = cleanup_old_activity_logs.apply_async(
            kwargs={"retain_years": 7, "manual_trigger": True}
        )
        await activity.log(
            action="BACKUP_TRIGGERED",
            resource_type="system",
            resource_id="activity_logs",
            description=f"Manual S3 backup triggered. Task ID: {task.id}",
            ip_address=request.client.host if request.client else None,
            actor_user_id=current_user.id,
        )
        return MessageResponse(message=f"Backup task queued (task_id={task.id}).")
    except Exception as e:
        logger.error("backup_dispatch_failed", error=str(e))
        raise HTTPException(
            status_code=503,
            detail="Could not queue backup task. Ensure Celery worker is running.",
        )


@router.post(
    "/maintenance/evaluate-all",
    response_model=MessageResponse,
    dependencies=[Depends(require_roles(*SUPER_ADMIN_ONLY))],
    summary="Trigger full portfolio compliance evaluation",
)
async def trigger_evaluate_all(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    activity = ActivityService(db)

    try:
        from app.worker.tasks import evaluate_all_companies
        task = evaluate_all_companies.apply_async(
            kwargs={"trigger_source": "ADMIN_MANUAL"}
        )
        await activity.log(
            action="PORTFOLIO_EVALUATION_TRIGGERED",
            resource_type="system",
            resource_id="all_companies",
            description=f"Full portfolio evaluation triggered by Super Admin. Task: {task.id}",
            ip_address=request.client.host if request.client else None,
            actor_user_id=current_user.id,
        )
        return MessageResponse(
            message=f"Full evaluation queued. Companies will be processed in batches (task_id={task.id})."
        )
    except Exception as e:
        logger.error("evaluate_all_dispatch_failed", error=str(e))
        raise HTTPException(status_code=503, detail="Could not queue evaluation task.")


@router.get(
    "/maintenance/worker-health",
    dependencies=[Depends(require_roles(*ADMIN_ROLES))],
    summary="Check Celery worker health",
)
async def worker_health(
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    try:
        from app.worker.celery_app import check_worker_health
        health = check_worker_health()
        return {
            **health,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        return {
            "status": "error",
            "active_workers": 0,
            "broker_reachable": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


