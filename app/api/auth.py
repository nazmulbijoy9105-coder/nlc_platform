import os
from urllib.parse import urlsplit

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.core.config import get_settings
from app.core.dependencies import get_auth_db, get_db_for_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    create_temp_token,
    decode_token,
    decrypt_totp_secret,
    hash_password,
    validate_password_strength,
    verify_password,
    verify_totp_code,
)
from app.models.database import AsyncSessionLocal, get_db, set_rls_context
from app.models.user import User
from app.services.notification_service import ActivityService
from app.services.user_service import UserService


def _limiter_storage_uri(settings) -> str:
    # Rate-limit storage must never inherit CELERY_BROKER_URL: Celery supports
    # brokers (for example AMQP) that are not valid SlowAPI Redis backends.
    redis_url = (settings.REDIS_URL or "").strip()
    parsed_scheme = urlsplit(redis_url).scheme.lower() if redis_url else ""
    if redis_url and parsed_scheme not in {"redis", "rediss"}:
        if settings.is_production_runtime:
            raise RuntimeError(
                "REDIS_URL for the auth rate limiter must use redis:// or rediss://; "
                "CELERY_BROKER_URL is not a substitute."
            )
        return "memory://"

    if settings.is_production_runtime:
        if not redis_url:
            raise RuntimeError(
                "A dedicated REDIS_URL is required for the auth rate limiter in production; "
                "CELERY_BROKER_URL is not a substitute and process-local memory storage "
                "would multiply the login allowance across replicas."
            )
        return redis_url
    return redis_url or "memory://"


def _build_limiter() -> Limiter:
    """Build the auth rate limiter (audit finding F-02).

    Mounts the dedicated REDIS_URL storage so buckets survive restarts and are shared
    across replicas. CELERY_BROKER_URL is never used as a limiter backend.
    Production and Render runtimes must configure Redis and refuse to start without it;
    the process-local ``memory://`` store is only selected outside production.
    Runtime Redis failures are deliberately not downgraded to process-local
    counters: doing so would reset the shared quota independently on each worker.

    Header emission is enabled so 429 responses carry ``Retry-After``. SlowAPI
    then writes rate-limit headers onto every limited endpoint's response, so
    each ``@limiter.limit`` endpoint must declare a ``response: Response``
    parameter.
    """
    return Limiter(
        key_func=get_remote_address,
        headers_enabled=True,
        storage_uri=_limiter_storage_uri(get_settings()),
        # SlowAPI performs synchronous storage operations while decorating
        # async routes. Bound both connection establishment and Redis commands
        # so an unresponsive Redis server cannot stall the worker indefinitely.
        storage_options={
            "socket_connect_timeout": 1.0,
            "socket_timeout": 1.0,
        },
        # One global fallback ceiling preserves login at 10/minute. The
        # route-specific 5/minute decorators remain the stricter 2FA limits.
        # Fallback is intentionally disabled: process-local counters cannot
        # preserve shared Redis quota across workers.
        in_memory_fallback=["10/minute"],
        in_memory_fallback_enabled=False,
    )


limiter = _build_limiter()
router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)

class LoginResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: dict
    requires_2fa: bool = False
    temp_token: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class Verify2FARequest(BaseModel):
    temp_token: str
    totp_code: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """MATCHES frontend types/index.ts User interface EXACTLY."""
    id: str
    email: str
    full_name: str
    role: str
    is_active: bool
    requires_2fa: bool  # ← frontend field name (was missing)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token, expected_type="access")
    jti = payload.get("jti") if payload else None
    if not payload or not isinstance(jti, str) or not jti:
        raise HTTPException(status_code=401, detail="Invalid or expired access token")
    from starlette.concurrency import run_in_threadpool

    from app.core.token_blacklist import BlacklistUnavailable, is_revoked
    try:
        if await run_in_threadpool(is_revoked, jti):
            raise HTTPException(status_code=401, detail="Token has been revoked")
    except BlacklistUnavailable:
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")
    return payload


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(request: Request, response: Response, body: LoginBody, db=Depends(get_auth_db)):
    """Login with lockout protection, failed attempt tracking, and 2FA support."""
    from app.services.user_service import UserService
    svc = UserService(db)
    
    user = await svc.get_by_email(body.email)
    if not user:
        # Don't reveal whether email exists — return generic error
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # The AUTH context is only for email lookup. Bind all subsequent reads,
    # lockout updates and login-attempt writes to this verified user identity.
    await set_rls_context(db, str(user.id))

    # Check account lockout
    if await svc.check_lockout(user):
        raise HTTPException(status_code=423, detail="Account temporarily locked due to too many failed attempts. Try again later.")
    
    # Verify credentials (increments failed attempts on wrong password)
    verified_user = await svc.verify_credentials(body.email, body.password)
    if not verified_user:
        # Audit log failed login
        # Persist this audit event in its own transaction: the request then
        # returns 401, so the request-scoped DB dependency correctly rolls back.
        async with AsyncSessionLocal() as audit_db:
            try:
                await set_rls_context(audit_db, str(user.id))
                await ActivityService(audit_db).log(
                    action="LOGIN_FAILED",
                    resource_type="user",
                    description=f"Failed login attempt for {body.email}",
                    actor_user_id=user.id,
                )
                await audit_db.commit()
            except Exception:
                await audit_db.rollback()
                raise
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verified_user.is_active:
        raise HTTPException(status_code=403, detail="Account deactivated")
    
    # Record successful login
    await svc.record_login(verified_user)
    await set_rls_context(db, str(verified_user.id))
    
    # Mandatory audit event: do not issue credentials if the audit insert fails.
    activity = ActivityService(db)
    await activity.log(
        action="LOGIN_SUCCESS",
        resource_type="user",
        resource_id=str(verified_user.id),
        description=f"User {verified_user.email} logged in successfully",
        actor_user_id=verified_user.id,
    )
    
    user_dict = {
        "id": str(verified_user.id),
        "email": verified_user.email,
        "full_name": verified_user.full_name,
        "role": str(verified_user.role),
        "is_active": verified_user.is_active,
        "requires_2fa": getattr(verified_user, "requires_2fa", False),
    }
    
    # Users who have completed TOTP enrollment must complete the challenge
    # before any access or refresh token is issued.
    if verified_user.totp_enabled:
        challenge = create_temp_token({"sub": str(verified_user.id)})
        return {
            "access_token": None,
            "refresh_token": None,
            "token_type": "bearer",
            "user": user_dict,
            "requires_2fa": True,
            "temp_token": challenge,
        }

    jwt_payload = await svc.build_jwt_payload(verified_user)
    access_token = create_access_token(jwt_payload)
    refresh_token = create_refresh_token(jwt_payload)

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": user_dict,
        "requires_2fa": False,
        "temp_token": None,
    }


@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user), db=Depends(get_db_for_user)):
    result = await db.execute(select(User).where(User.id == current_user["sub"]))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=str(user.id),
        email=user.email,
        full_name=user.full_name,
        role=str(user.role),
        is_active=user.is_active,
        requires_2fa=getattr(user, "requires_2fa", False),  # ← FIX
    )



@router.post("/2fa/setup")
async def setup_2fa(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_for_user),
):
    """Start TOTP setup for the authenticated, active user."""
    user_id = current_user.get("sub") or current_user.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid access token")

    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if user.totp_enabled:
        raise HTTPException(status_code=409, detail="Two-factor authentication is already enabled")

    setup = await UserService(db).setup_totp(user)
    return {
        "message": "TOTP setup initiated. Confirm a code before enabling 2FA.",
        **setup,
    }


class VerifyTOTPSetupRequest(BaseModel):
    totp_code: str = Field(pattern=r"^\d{6}$")


@router.post("/2fa/confirm")
@limiter.limit("5/minute")
async def confirm_2fa_setup(
    request: Request,
    response: Response,
    body: VerifyTOTPSetupRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db_for_user),
):
    """Enable TOTP only after the authenticated user proves possession."""
    user_id = current_user.get("sub") or current_user.get("user_id")
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if not user.totp_secret_encrypted:
        raise HTTPException(status_code=400, detail="Start 2FA setup before confirming")
    if user.totp_enabled:
        raise HTTPException(status_code=409, detail="Two-factor authentication is already enabled")
    if not await UserService(db).confirm_totp(user, body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")
    return {"status": "enabled", "requires_2fa": True}


@router.post("/verify-2fa", response_model=LoginResponse)
@limiter.limit("5/minute")
async def verify_2fa(
    request: Request, response: Response, body: Verify2FARequest, db=Depends(get_db)
):
    """Verify a single-use 2FA challenge and then issue full tokens."""
    payload = decode_token(body.temp_token, expected_type="temp")
    jti = payload.get("jti") if payload else None
    exp = payload.get("exp") if payload else None
    user_id = payload.get("sub") if payload else None
    if not payload or not isinstance(jti, str) or not jti or not exp:
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA challenge")

    await set_rls_context(db, str(user_id))
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    if not user.totp_enabled or not user.totp_secret_encrypted:
        raise HTTPException(status_code=403, detail="Two-factor authentication is not enabled")

    if not verify_totp_code(decrypt_totp_secret(user.totp_secret_encrypted), body.totp_code):
        raise HTTPException(status_code=401, detail="Invalid 2FA code")

    from app.core.token_blacklist import BlacklistUnavailable, consume_temp_token
    try:
        if not consume_temp_token(jti, exp):
            raise HTTPException(status_code=401, detail="2FA challenge has already been used")
    except BlacklistUnavailable:
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")

    svc = UserService(db)
    jwt_payload = await svc.build_jwt_payload(user)
    user_dict = {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": str(user.role),
        "is_active": user.is_active,
        "requires_2fa": True,
    }
    return LoginResponse(
        access_token=create_access_token(jwt_payload),
        refresh_token=create_refresh_token(jwt_payload),
        token_type="bearer",
        user=user_dict,
        requires_2fa=False,
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(body: RefreshRequest, db=Depends(get_db)):
    """Exchange a valid refresh token for a new access token."""
    payload = decode_token(body.refresh_token, expected_type="refresh")
    if not payload or not payload.get("sub"):
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    await set_rls_context(db, str(payload["sub"]))
    result = await db.execute(select(User).where(User.id == payload.get("sub")))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or deactivated")
    # SEC-006: atomically consume the old refresh token; reject replay.
    from app.core.token_blacklist import BlacklistUnavailable, consume_refresh_token
    old_jti = payload.get("jti")
    old_exp = payload.get("exp")
    if not isinstance(old_jti, str) or not old_jti or not old_exp:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    from app.core.token_blacklist import is_revoked
    try:
        if is_revoked(old_jti, fail_closed=True):
            raise HTTPException(status_code=401, detail="Refresh token has been revoked")
        consumed = consume_refresh_token(old_jti, old_exp)
    except BlacklistUnavailable:
        raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable")
    if not consumed:
        raise HTTPException(status_code=401, detail="Refresh token has already been used")

    # Rebuild authorization claims from current database memberships.
    jwt_payload = await UserService(db).build_jwt_payload(user)
    new_access = create_access_token(jwt_payload)
    new_refresh = create_refresh_token(jwt_payload)
    return RefreshResponse(access_token=new_access, refresh_token=new_refresh, token_type="bearer")


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


@router.post("/logout")
async def logout(
    body: LogoutRequest = Body(default=LogoutRequest()),
    current_user: dict = Depends(get_current_user),
    token: str = Depends(oauth2_scheme),
):
    """Revoke the current access token and, when supplied, its refresh token.

    Never report a successful logout when Redis failed to persist revocation:
    the access token would otherwise remain usable until its expiry.
    """
    from app.core.token_blacklist import revoke

    access_payload = decode_token(token, expected_type="access") or {}
    access_jti = access_payload.get("jti")
    if (
        not isinstance(access_jti, str)
        or not access_jti
        or access_payload.get("sub") != current_user.get("sub")
    ):
        raise HTTPException(status_code=401, detail="Invalid access token for logout")

    access_revoked = revoke(access_jti, access_payload.get("exp"))
    if not access_revoked:
        raise HTTPException(
            status_code=503,
            detail="Logout could not revoke the access token. The session may remain active; retry.",
        )

    refresh_revoked = False
    if body.refresh_token:
        refresh_payload = decode_token(body.refresh_token, expected_type="refresh")
        if refresh_payload and refresh_payload.get("sub") == current_user.get("sub"):
            refresh_jti = refresh_payload.get("jti")
            if not isinstance(refresh_jti, str) or not refresh_jti:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid refresh token supplied for logout",
                )
            refresh_revoked = revoke(refresh_jti, refresh_payload.get("exp"))
            if not refresh_revoked:
                raise HTTPException(
                    status_code=503,
                    detail=(
                        "Access token was revoked, but refresh-token revocation failed. "
                        "The refresh session may remain active; retry."
                    ),
                )

    return {
        "status": "logged_out",
        "access_revoked": access_revoked,
        "refresh_revoked": refresh_revoked,
        "user_id": current_user.get("sub"),
    }

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password", response_model=dict)
async def change_password(
    body: ChangePasswordRequest,
    token: str = Depends(oauth2_scheme),
    db=Depends(get_db_for_user),
):
    """Change password with strength validation."""
    payload = await get_current_user(token)
    
    result = await db.execute(select(User).where(User.id == payload.get("sub")))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_password(body.current_password, user.password_hash):
        raise HTTPException(status_code=401, detail="Current password incorrect")
    
    # Validate new password strength
    is_strong, msg = validate_password_strength(body.new_password)
    if not is_strong:
        raise HTTPException(status_code=422, detail=msg)
    
    # Update password
    user.password_hash = hash_password(body.new_password)
    await db.commit()
    
    return {"status": "password_changed"}


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "LEGAL_STAFF"


@router.post("/signup", response_model=dict)
async def signup(body: SignupRequest, db=Depends(get_auth_db)):
    """Public signup — creates a new user account.
    
    Available roles: LEGAL_STAFF, ADMIN_STAFF, CLIENT_DIRECTOR, CLIENT_VIEW_ONLY
    SUPER_ADMIN cannot be created via signup (only via setup-admin).
    """
    from app.core.security import hash_password, validate_password_strength
    from app.models.enums import UserRole
    from app.models.user import User
    
    # POLICY: Public signup allowed, defaults to CLIENT_VIEW_ONLY (lowest role).
    # Role escalation blocked. SUPER_ADMIN only via env ADMIN_EMAIL/ADMIN_PASSWORD.
    # POLICY: Public signup allowed, defaults to CLIENT_VIEW_ONLY (lowest role).
    # Role escalation blocked. SUPER_ADMIN only via env ADMIN_EMAIL/ADMIN_PASSWORD.
    if os.environ.get("ALLOW_PUBLIC_SIGNUP", "true").lower() != "true":
        raise HTTPException(status_code=403, detail="Signup is disabled")

    # Check if email exists
    existing = await db.execute(select(User).where(User.email == body.email.lower().strip()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    
    # Validate password strength
    is_strong, msg = validate_password_strength(body.password)
    if not is_strong:
        raise HTTPException(status_code=422, detail=msg)
    
    # Create user
    user = User(
        email=body.email.lower().strip(),
        full_name=body.full_name,
        role=UserRole.CLIENT_VIEW_ONLY,
        password_hash=hash_password(body.password),
        is_active=True,
    )
    db.add(user)
    await db.commit()
    
    # Auto-login: return tokens
    access_token = create_access_token({
        "sub": str(user.id), "user_id": str(user.id),
        "email": user.email, "role": str(user.role), "type": "access"
    })
    refresh_token = create_refresh_token({
        "sub": str(user.id), "user_id": str(user.id),
        "email": user.email, "role": str(user.role), "type": "refresh"
    })
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "role": str(user.role),
            "is_active": True,
            "requires_2fa": False,
        }
    }
