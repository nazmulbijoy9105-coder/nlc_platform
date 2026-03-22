"""
app/api/auth.py — Authentication Router
NEUM LEX COUNSEL

Endpoints:
  POST /auth/login          Step 1: email + password → temp token
  POST /auth/2fa/verify     Step 2: TOTP code → access + refresh tokens
  POST /auth/2fa/setup      Setup TOTP for a user (first-time / reset)
  POST /auth/2fa/confirm    Confirm TOTP setup (activate 2FA)
  POST /auth/refresh        Exchange refresh token → new access token
  POST /auth/logout         Invalidate session (client-side token drop)
  GET  /auth/me             Current user profile
  POST /auth/change-password Change own password

Flow:
  1. POST /login  → validates credentials → returns temp_token (type: "2fa_pending")
  2. POST /2fa    → validates TOTP against temp_token → returns access_token + refresh_token
  3. All subsequent requests: Authorization: Bearer <access_token>

AI Constitution compliance:
  - Failed login attempts tracked, account locked after 5 failures
  - All auth events written to user_activity_logs
  - 2FA is mandatory for all roles
  - Passwords never returned in any response
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.dependencies import get_db, get_current_user, get_db_for_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_temp_token,
    decode_token,
)
from app.models.user import User
from app.services.user_service import UserService
from app.services.notification_service import ActivityService

logger = structlog.get_logger(__name__)
settings = get_settings()
router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginResponse(BaseModel):
    """Step-1 response — temp token for 2FA verification."""
    temp_token: str
    message: str = "Please complete two-factor authentication."
    totp_required: bool = True
    user_id: str
    email: str
    role: str


class TwoFactorRequest(BaseModel):
    temp_token: str
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    """Full auth token pair returned after successful 2FA."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user_id: str
    email: str
    role: str
    full_name: str
    company_ids: list[str]


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)


class TOTPSetupResponse(BaseModel):
    totp_secret: str         # base32 encoded secret for QR generation
    qr_uri: str              # otpauth:// URI for authenticator apps
    manual_entry_key: str    # human-readable groups for manual entry
    message: str = "Scan the QR code with your authenticator app, then confirm with a code."


class TOTPConfirmRequest(BaseModel):
    totp_code: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class UserProfileResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    totp_enabled: bool
    last_login_at: Optional[datetime]
    company_ids: list[str]
    created_at: datetime


class MessageResponse(BaseModel):
    message: str
    success: bool = True


# ---------------------------------------------------------------------------
# Helper: build full TokenResponse from authenticated user
# ---------------------------------------------------------------------------

async def _build_token_response(user: User, db: AsyncSession) -> TokenResponse:
    svc = UserService(db)
    payload = await svc.build_jwt_payload(user)
    company_ids = await svc.get_company_ids(user.id)

    access_token = create_access_token(payload)
    refresh_token = create_refresh_token(str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        full_name=user.full_name,
        company_ids=[str(cid) for cid in company_ids],
    )


# ---------------------------------------------------------------------------
# POST /auth/login — Step 1: email + password
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Step 1: Authenticate with email and password",
    description=(
        "Validates credentials. Returns a short-lived `temp_token` to be used "
        "with the `/auth/2fa/verify` endpoint. The account is locked after 5 "
        "consecutive failed attempts."
    ),
)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = UserService(db)
    activity = ActivityService(db)

    # Look up user
    user = await svc.get_by_email(body.email)
    if not user:
        # Generic message — do not reveal whether email exists
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Check lockout before verifying password
    is_locked = await svc.check_lockout(user)
    if is_locked:
        logger.warning("login_account_locked", user_id=str(user.id), email=user.email)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Account is temporarily locked due to too many failed attempts. "
                f"Please try again later or contact NLC support."
            ),
        )

    # Verify password
    authenticated = await svc.verify_credentials(body.email, body.password)
    if not authenticated:
        await svc.increment_failed_attempts(user)
        await activity.log(
            action="LOGIN_FAILED",
            resource_type="user",
            resource_id=str(user.id),
            description=f"Failed login attempt for {body.email}",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            actor_user_id=user.id,
        )
        logger.warning("login_failed_credentials", email=body.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Verify user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated. Please contact NLC support.",
        )

    # Reset failed attempts on successful password verification
    await svc.reset_failed_attempts(user)

    # Issue temp token (2FA not yet done)
    temp_token = create_temp_token(
        user_id=str(user.id),
        email=user.email,
        role=user.role,
    )

    logger.info("login_step1_ok", user_id=str(user.id), role=user.role)

    return LoginResponse(
        temp_token=temp_token,
        user_id=str(user.id),
        email=user.email,
        role=user.role,
        totp_required=user.totp_enabled,
    )


# ---------------------------------------------------------------------------
# POST /auth/2fa/verify — Step 2: TOTP code
# ---------------------------------------------------------------------------

@router.post(
    "/2fa/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Step 2: Verify TOTP code and receive access token",
)
async def verify_2fa(
    body: TwoFactorRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # Decode and validate the temp token
    try:
        claims = decode_token(body.temp_token, expected_type="2fa_pending")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session. Please log in again.",
        )

    user_id = claims.get("sub")
    svc = UserService(db)
    activity = ActivityService(db)

    user = await svc.get_by_id_or_404(uuid.UUID(user_id))

    # Verify TOTP code
    totp_ok = await svc.verify_totp(user, body.totp_code)
    if not totp_ok:
        await activity.log(
            action="2FA_FAILED",
            resource_type="user",
            resource_id=str(user.id),
            description="TOTP verification failed",
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            actor_user_id=user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired two-factor code. Please try again.",
        )

    # Record successful login
    await svc.record_login(user)
    await activity.log(
        action="LOGIN_SUCCESS",
        resource_type="user",
        resource_id=str(user.id),
        description=f"Successful login for {user.email}",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        actor_user_id=user.id,
    )

    logger.info("login_complete", user_id=str(user.id), role=user.role)
    return await _build_token_response(user, db)


# ---------------------------------------------------------------------------
# POST /auth/2fa/setup — Initialise TOTP for a user
# ---------------------------------------------------------------------------

@router.post(
    "/2fa/setup",
    response_model=TOTPSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate a new TOTP secret for the current user",
    description="Returns QR URI. User must confirm with /2fa/confirm before 2FA is activated.",
)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    result = await svc.setup_totp(current_user)
    return TOTPSetupResponse(
        totp_secret=result["totp_secret"],
        qr_uri=result["qr_uri"],
        manual_entry_key=result["manual_entry_key"],
    )


# ---------------------------------------------------------------------------
# POST /auth/2fa/confirm — Activate 2FA after scanning QR
# ---------------------------------------------------------------------------

@router.post(
    "/2fa/confirm",
    response_model=MessageResponse,
    summary="Confirm TOTP setup and activate two-factor authentication",
)
async def confirm_2fa(
    body: TOTPConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    confirmed = await svc.confirm_totp(current_user, body.totp_code)
    if not confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP code is incorrect. Please ensure your authenticator app is synced.",
        )
    return MessageResponse(message="Two-factor authentication has been enabled successfully.")


# ---------------------------------------------------------------------------
# POST /auth/refresh — Exchange refresh token for new access token
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Exchange a refresh token for a new access token",
)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        claims = decode_token(body.refresh_token, expected_type="refresh")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token. Please log in again.",
        )

    user_id = claims.get("sub")
    svc = UserService(db)
    user = await svc.get_by_id_or_404(uuid.UUID(user_id))

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated.",
        )

    return await _build_token_response(user, db)


# ---------------------------------------------------------------------------
# POST /auth/logout — Client-side logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Log out (invalidate session client-side)",
    description=(
        "NLC uses stateless JWTs. Logout instructs the client to discard its tokens. "
        "For server-side revocation, tokens expire per their TTL."
    ),
)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    activity = ActivityService(db)
    await activity.log(
        action="LOGOUT",
        resource_type="user",
        resource_id=str(current_user.id),
        description="User logged out",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        actor_user_id=current_user.id,
    )
    logger.info("logout", user_id=str(current_user.id))
    return MessageResponse(message="Logged out successfully. Please discard your tokens.")


# ---------------------------------------------------------------------------
# GET /auth/me — Current user profile
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="Get the current authenticated user's profile",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    svc = UserService(db)
    company_ids = await svc.get_company_ids(current_user.id)
    return UserProfileResponse(
        user_id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active,
        totp_enabled=current_user.totp_enabled,
        last_login_at=current_user.last_login_at,
        company_ids=[str(cid) for cid in company_ids],
        created_at=current_user.created_at,
    )


# ---------------------------------------------------------------------------
# POST /auth/change-password
# ---------------------------------------------------------------------------

@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Change the current user's password",
)
async def change_password(
    body: ChangePasswordRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_for_user),
):
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must differ from current password.",
        )

    svc = UserService(db)
    activity = ActivityService(db)

    success = await svc.change_password(
        user=current_user,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    await activity.log(
        action="PASSWORD_CHANGED",
        resource_type="user",
        resource_id=str(current_user.id),
        description="Password changed successfully",
        ip_address=request.client.host if request.client else None,
        actor_user_id=current_user.id,
    )
    return MessageResponse(message="Password changed successfully.")
