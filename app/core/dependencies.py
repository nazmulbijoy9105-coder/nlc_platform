"""
NEUM LEX COUNSEL — FastAPI Dependency Injection
app/core/dependencies.py

Every dependency used in API route handlers lives here.
These functions are injected via Depends() and handle:
  - Database session management (async + RLS context)
  - JWT verification and token parsing
  - Role-based access control (RBAC)
  - Multi-tenant company isolation
  - Pagination parameters
  - Request ID propagation
  - Rule engine singleton access

AI Constitution Article 2: Role and company access enforced on EVERY request.
No request touches data without passing through these dependencies.

Usage:
    @router.get("/companies/{company_id}")
    async def get_company(
        company_id: UUID,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user),
        _: str = Depends(require_company_access(company_id)),
    ):
        ...
"""
from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.bearer import Bearer401
from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.models.database import AsyncSessionLocal, set_admin_context, set_app_role, set_auth_context, set_catalog_context, set_rls_context
from app.models.enums import UserRole
from app.models.user import User

# ── HTTP Bearer scheme ───────────────────────────────────────────────
_bearer = Bearer401(auto_error=True, scheme_name="HTTPBearer")


# ═══════════════════════════════════════════════════════════════════════
# TOKEN DATA MODEL
# ═══════════════════════════════════════════════════════════════════════

class TokenData(BaseModel):
    """
    Parsed JWT payload. Attached to every authenticated request.
    company_ids: list of company UUIDs this user is authorized to access.
    Admin/Staff users have company_ids = [] (they access via RLS ADMIN context).
    """
    user_id:     str
    email:       str
    role:        str
    company_ids: list[str] = []

    @property
    def user_uuid(self) -> uuid.UUID:
        return uuid.UUID(self.user_id)

    @property
    def is_admin(self) -> bool:
        return self.role in (UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def is_legal_staff(self) -> bool:
        return self.role == UserRole.LEGAL_STAFF

    @property
    def is_client(self) -> bool:
        return self.role in (UserRole.CLIENT_DIRECTOR, UserRole.CLIENT_VIEW_ONLY)


# ═══════════════════════════════════════════════════════════════════════
# DATABASE SESSION
# ═══════════════════════════════════════════════════════════════════════

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session.
    Commits on success, rolls back on exception, always closes.
    NOTE: RLS context is NOT set here. Use only for auth flows that set
    AUTH or a verified user identity before querying protected tables, or
    secret-validated jobs that call set_admin_context. Tenant routes must use
    get_db_for_user(); privileged routes must use the verified admin path.
    """
    async with AsyncSessionLocal() as session:
        try:
            await set_app_role(session)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_catalog_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Public read-only catalogue session. RLS permits CATALOG context only on
    authenticated/public legal-reference tables; tenant tables remain denied.
    """
    async with AsyncSessionLocal() as session:
        try:
            await set_catalog_context(session)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_auth_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield a least-privilege session for login/signup only.
    AUTH context is permitted by RLS on users, not tenant or company tables.
    """
    async with AsyncSessionLocal() as session:
        try:
            await set_auth_context(session)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ═══════════════════════════════════════════════════════════════════════
# TOKEN VERIFICATION
# ═══════════════════════════════════════════════════════════════════════

def _check_token_blacklist(jti: str) -> bool:
    """
    Check if token is revoked via Redis blacklist.
    Returns True if revoked.
    Raises HTTP 401 if Redis is unavailable (fail closed — RDS-01).
    """
    from fastapi import HTTPException, status

    from app.core.token_blacklist import BlacklistUnavailable, is_revoked
    try:
        return is_revoked(jti, fail_closed=True)
    except BlacklistUnavailable:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication service temporarily unavailable. Please retry.",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> TokenData:
    """
    Verify JWT Bearer token and return parsed TokenData.
    Checks token blacklist for revoked tokens.
    Raises 401 on invalid/expired/revoked token.
    """
    payload = decode_token(credentials.credentials, expected_type="access")
    if payload is None or not isinstance(payload.get("jti"), str) or not payload.get("jti"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token blacklist (revoked on logout)
    jti = payload.get("jti")
    if jti and _check_token_blacklist(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return TokenData(
        user_id=str(payload.get("user_id") or payload.get("sub") or ""),
            email=payload["email"],
            role=payload["role"],
            company_ids=payload.get("company_ids", []),
        )
    except (KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


# ═══════════════════════════════════════════════════════════════════════
# CURRENT USER LOADING
# ═══════════════════════════════════════════════════════════════════════

async def get_current_user(
    token: TokenData = Depends(verify_access_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Load the full User ORM object from DB after JWT verification.
    Sets the PostgreSQL RLS context for the session.
    Raises 401 if user not found or deactivated.
    """
    from sqlalchemy import select

    from app.models.user import User as UserModel

    # Set RLS context so all queries in this session are scoped
    await set_rls_context(db, token.user_id)

    result = await db.execute(
        select(UserModel).where(
            UserModel.id == uuid.UUID(token.user_id),
            UserModel.is_active,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Authorization is always based on the current database role, never a stale JWT claim.
    db_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if db_role != token.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account permissions changed. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_with_db(  # type: ignore
    token: TokenData = Depends(verify_access_token),
) -> tuple[User, AsyncSession]:
    """
    Returns (user, session) together.
    Use when the service needs both the user and session passed together.
    """
    async with AsyncSessionLocal() as db:
        await set_rls_context(db, token.user_id)
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(token.user_id), User.is_active)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found.")
        db_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if db_role != token.role:
            raise HTTPException(status_code=401, detail="Account permissions changed. Please sign in again.")
        yield user, db
        await db.commit()


# ═══════════════════════════════════════════════════════════════════════
# ROLE-BASED ACCESS CONTROL
# ═══════════════════════════════════════════════════════════════════════

def require_roles(*allowed_roles: str):
    """
    RBAC dependency factory. Returns a dependency that enforces role membership.
    Raises 403 if the authenticated user's role is not in allowed_roles.

    Usage:
        @router.post("/companies")
        async def create_company(
            _: TokenData = Depends(require_roles("SUPER_ADMIN", "ADMIN_STAFF"))
        ):
    """
    async def _check_role(
        token: TokenData = Depends(verify_access_token),
        db: AsyncSession = Depends(get_db),
    ) -> TokenData:
        # Reload role from the database on every privileged request. JWT role
        # claims can outlive an administrator's role downgrade.
        await set_rls_context(db, token.user_id)
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(token.user_id), User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User account is inactive or unavailable.")
        db_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if db_role != token.role:
            raise HTTPException(status_code=401, detail="Account permissions changed. Please sign in again.")
        if db_role not in [str(getattr(role, "value", role)) for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. This action requires one of: {list(allowed_roles)}.",
            )
        return token
    return _check_role


# Module-level callables — FastAPI resolves these directly via Depends().
# DO NOT wrap in a function: that returns the inner _check_role without
# calling it, silently bypassing authentication on every admin endpoint.
require_admin = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)
require_super_admin = require_roles(UserRole.SUPER_ADMIN)
require_staff = require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF)


async def get_admin_db(
    token: TokenData = Depends(require_super_admin),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an ADMIN-context session only after live database-backed
    SUPER_ADMIN authorization. Background workers must use their separately
    verified service-task path, not this HTTP dependency.
    """
    async with AsyncSessionLocal() as session:
        try:
            await set_admin_context(session)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ═══════════════════════════════════════════════════════════════════════
# SUPER ADMIN IP WHITELIST
# ═══════════════════════════════════════════════════════════════════════

def require_super_admin_ip(
    request: Request,
    token: TokenData = Depends(require_roles(UserRole.SUPER_ADMIN)),
    settings: Settings = Depends(get_settings),
) -> TokenData:
    """
    Verify Super Admin is calling from a whitelisted IP.
    Only enforced if super_admin_ip_whitelist is non-empty in settings.
    Security: Nginx passes real IP in X-Real-IP or X-Forwarded-For.
    """
    if token.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=403, detail="Super Admin access required.")

    whitelist = settings.super_admin_ip_whitelist
    if not whitelist:
        return token  # No restriction configured

    client_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "")
    )

    if client_ip not in whitelist:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Super Admin access from {client_ip} is not authorized.",
        )
    return token


# ═══════════════════════════════════════════════════════════════════════
# MULTI-TENANT COMPANY ACCESS
# ═══════════════════════════════════════════════════════════════════════

def require_company_access(company_id_param: str = "company_id"):
    """
    Dependency factory that validates the requesting user has access
    to the company specified in the path parameter.

    Platform admins: portfolio-wide access.
    Legal staff: must be assigned to the company or hold an active company
    access row. Client roles: must hold a live active company membership;
    JWT company_ids are informational and are never trusted for authorization.
    Platform admins: portfolio-wide access. Legal staff must be assigned
    to the company or hold an active company access row. Client roles require
    a live active company membership; JWT company_ids are never trusted.

    Usage:
        @router.get("/companies/{company_id}/compliance")
        async def get_compliance(
            company_id: UUID,
            _: str = Depends(require_company_access()),
            token: TokenData = Depends(verify_access_token),
        ):
    """
    async def _check_access(
        company_id: uuid.UUID,
        token: TokenData = Depends(verify_access_token),
        db: AsyncSession = Depends(get_db),
    ) -> uuid.UUID:
        # Re-check active user and current role; do not trust stale company_ids
        # embedded in a JWT after a membership has been revoked.
        await set_rls_context(db, token.user_id)
        from sqlalchemy import select
        result = await db.execute(
            select(User).where(User.id == uuid.UUID(token.user_id), User.is_active.is_(True))
        )
        user = result.scalar_one_or_none()
        if user is None:
            raise HTTPException(status_code=401, detail="User account is inactive or unavailable.")
        db_role = user.role.value if hasattr(user.role, "value") else str(user.role)
        if db_role != token.role:
            raise HTTPException(status_code=401, detail="Account permissions changed. Please sign in again.")

        if db_role in ("SUPER_ADMIN", "ADMIN_STAFF"):
            return company_id
        if db_role == "LEGAL_STAFF":
            from app.core.company_authorization import ensure_staff_company_scope

            await ensure_staff_company_scope(company_id, user, db)
            return company_id

        from app.models.company import CompanyUserAccess
        membership = await db.execute(
            select(CompanyUserAccess.id).where(
                CompanyUserAccess.user_id == uuid.UUID(token.user_id),
                CompanyUserAccess.company_id == company_id,
                CompanyUserAccess.is_active.is_(True),
            ).limit(1)
        )
        if membership.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this company.",
            )
        return company_id

    return _check_access


async def get_client_company_filter(
    token: TokenData = Depends(verify_access_token),
    db: AsyncSession = Depends(get_db),
) -> list[str] | None:
    """
    Return a live company filter from active database memberships.
    JWT company_ids are informational only and may be stale after revocation.
    """
    await set_rls_context(db, token.user_id)
    from sqlalchemy import select
    user_result = await db.execute(
        select(User).where(
            User.id == uuid.UUID(token.user_id),
            User.is_active.is_(True),
        )
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User account is inactive or unavailable.")
    db_role = user.role.value if hasattr(user.role, "value") else str(user.role)
    if db_role != token.role:
        raise HTTPException(status_code=401, detail="Account permissions changed. Please sign in again.")

    if db_role in ("SUPER_ADMIN", "ADMIN_STAFF"):
        return None

    from app.models.company import Company, CompanyUserAccess
    if db_role == "LEGAL_STAFF":
        assigned = await db.execute(
            select(Company.id).where(Company.assigned_staff_id == user.id)
        )
        memberships = await db.execute(
            select(CompanyUserAccess.company_id).where(
                CompanyUserAccess.user_id == user.id,
                CompanyUserAccess.is_active.is_(True),
            )
        )
        return [
            str(company_id)
            for company_id in dict.fromkeys([
                *assigned.scalars().all(),
                *memberships.scalars().all(),
            ])
        ]

    membership_result = await db.execute(
        select(CompanyUserAccess.company_id).where(
            CompanyUserAccess.user_id == uuid.UUID(token.user_id),
            CompanyUserAccess.is_active.is_(True),
        )
    )
    return [str(company_id) for company_id in membership_result.scalars().all()]


# ═══════════════════════════════════════════════════════════════════════
# REVENUE / ADMIN-ONLY GUARD
# ═══════════════════════════════════════════════════════════════════════

def require_revenue_access(
    token: TokenData = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)),
) -> TokenData:
    """
    Guard for revenue, engagement, and pipeline endpoints.
    AI Constitution Article 2.2: Revenue data never shown to client roles.
    Only SUPER_ADMIN and ADMIN_STAFF may access this data.
    """
    if token.role not in (UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Revenue intelligence data is restricted to admin users only.",
        )
    return token


# ═══════════════════════════════════════════════════════════════════════
# PAGINATION
# ═══════════════════════════════════════════════════════════════════════

class PaginationParams(BaseModel):
    page: int = 1
    page_size: int = 25
    offset: int = 0

    @property
    def limit(self) -> int:
        return self.page_size


def get_pagination(
    page: int = 1,
    page_size: int = 25,
    settings: Settings = Depends(get_settings),
) -> PaginationParams:
    """
    Standard pagination dependency.
    page: 1-based page number.
    page_size: records per page (capped at settings.max_page_size).
    """
    if page < 1:
        page = 1
    page_size = min(page_size, settings.max_page_size)
    page_size = max(page_size, 1)
    offset = (page - 1) * page_size
    return PaginationParams(page=page, page_size=page_size, offset=offset)


# ═══════════════════════════════════════════════════════════════════════
# REQUEST ID
# ═══════════════════════════════════════════════════════════════════════

def get_request_id(request: Request) -> str:
    """
    Extract or generate a request correlation ID.
    Nginx injects X-Request-ID. If missing, generate one.
    All log lines and activity logs use this ID for correlation.
    """
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


# ═══════════════════════════════════════════════════════════════════════
# RULE ENGINE FACTORY
# ═══════════════════════════════════════════════════════════════════════

def get_rule_engine():
    """Return an isolated engine for one evaluation.

    NLCRuleEngine keeps mutable per-evaluation state (flags and evaluation
    date). Sharing an instance across concurrent requests can mix companies'
    findings and dates, so production callers must never receive a singleton.
    """
    from app.rule_engine import NLCRuleEngine
    return NLCRuleEngine()


async def get_db_for_user(
    token: TokenData = Depends(verify_access_token),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an authenticated database session with identity-bound RLS context.

    Every human user, including staff, receives an identity-bound UUID context.
    ADMIN context is reserved for explicitly trusted service/background sessions.
    Every human account keeps its signed user UUID. Only trusted internal
    service operations use the ADMIN principal; staff permissions are derived
    from the active database user row and the relevant RLS helper.
    """
    async with AsyncSessionLocal() as session:
        try:
            role_value = str(getattr(token.role, "value", token.role))
            # Every human account, including SUPER_ADMIN and ADMIN_STAFF,
            # retains its signed UUID. ADMIN is reserved for trusted internal
            # service/cron operations, never an authenticated human session.
            try:
                user_uuid = uuid.UUID(token.user_id)
            except (TypeError, ValueError):
                raise HTTPException(status_code=401, detail="Invalid authenticated user identity.")

            # Keep the signed principal bound to the actual human identity.
            # RLS helpers derive privileges from the active database role;
            # a JWT role claim never becomes the trusted ADMIN principal.
            await set_rls_context(session, token.user_id)

            result = await session.execute(
                select(User).where(
                    User.id == user_uuid,
                    User.is_active.is_(True),
                )
            )
            user = result.scalar_one_or_none()
            if user is None:
                raise HTTPException(status_code=401, detail="User account is inactive or unavailable.")

            db_role = user.role.value if hasattr(user.role, "value") else str(user.role)
            if db_role != role_value:
                raise HTTPException(status_code=401, detail="Account permissions changed. Please sign in again.")

            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ANNOTATED SHORTHAND TYPES
# (Use in function signatures for cleaner code)
# ═══════════════════════════════════════════════════════════════════════

# Type aliases for common dependencies
DBSession    = Annotated[AsyncSession, Depends(get_db)]
AdminDB      = Annotated[AsyncSession, Depends(get_admin_db)]
CurrentToken = Annotated[TokenData, Depends(verify_access_token)]
CurrentUser  = Annotated[User, Depends(get_current_user)]
Pagination = PaginationParams
RequestID    = Annotated[str, Depends(get_request_id)]
AppSettings  = Annotated[Settings, Depends(get_settings)]
AdminAccess  = Annotated[TokenData, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF))]
SuperAdmin   = Annotated[TokenData, Depends(require_roles(UserRole.SUPER_ADMIN))]
StaffAccess  = Annotated[TokenData, Depends(require_roles(
    UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF
))]
RevenueAccess = Annotated[TokenData, Depends(require_revenue_access)]


# Alias for backward compatibility

