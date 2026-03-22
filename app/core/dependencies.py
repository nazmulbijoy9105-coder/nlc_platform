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
from typing import Annotated, List, Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.security import decode_token
from app.models.database import AsyncSessionLocal, set_admin_context, set_rls_context
from app.models.enums import UserRole
from app.models.user import User

# ── HTTP Bearer scheme ───────────────────────────────────────────────
_bearer = HTTPBearer(auto_error=True)


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
    company_ids: List[str] = []

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

async def get_db() -> AsyncSession:
    """
    Yield an async database session.
    Commits on success, rolls back on exception, always closes.
    NOTE: RLS context is NOT set here — it is set by get_db_for_user()
    which requires the authenticated user. Use this only for
    admin-context operations (background jobs, seeding, migrations).
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_admin_db() -> AsyncSession:
    """
    Yield a DB session with ADMIN RLS context.
    Use for: background cron jobs, Celery tasks, Super Admin operations.
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
# TOKEN VERIFICATION
# ═══════════════════════════════════════════════════════════════════════

def verify_access_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> TokenData:
    """
    Verify JWT Bearer token and return parsed TokenData.
    Called as the first step in every authenticated dependency.
    Raises 401 on invalid/expired token.
    """
    try:
        payload = decode_token(credentials.credentials, expected_type="access")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        return TokenData(
            user_id=payload["user_id"],
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


def verify_temp_token(
    credentials: HTTPAuthorizationCredentials = Security(_bearer),
) -> TokenData:
    """
    Verify a temp (2FA step) JWT.
    Used only on the /auth/verify-2fa endpoint.
    """
    try:
        payload = decode_token(credentials.credentials, expected_type="temp_2fa")
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired 2FA session. Please login again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    return TokenData(
        user_id=payload["user_id"],
        email=payload["email"],
        role=payload["role"],
        company_ids=[],
    )


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
            UserModel.is_active == True,
        )
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or has been deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify role hasn't changed since token was issued
    if user.role != token.role:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Role mismatch. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def get_current_user_with_db(
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
            select(User).where(User.id == uuid.UUID(token.user_id), User.is_active == True)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=401, detail="User not found.")
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
    def _check_role(token: TokenData = Depends(verify_access_token)) -> TokenData:
        if token.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. This action requires one of: "
                    f"{list(allowed_roles)}. Your role: {token.role}"
                ),
            )
        return token
    return _check_role


def require_admin() -> TokenData:
    """Shortcut: SUPER_ADMIN or ADMIN_STAFF only."""
    return require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF)


def require_super_admin() -> TokenData:
    """Shortcut: SUPER_ADMIN only. Used for rule changes, user management."""
    return require_roles(UserRole.SUPER_ADMIN)


def require_staff() -> TokenData:
    """Shortcut: SUPER_ADMIN, ADMIN_STAFF, or LEGAL_STAFF."""
    return require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF)


# ═══════════════════════════════════════════════════════════════════════
# SUPER ADMIN IP WHITELIST
# ═══════════════════════════════════════════════════════════════════════

def require_super_admin_ip(
    request: Request,
    token: TokenData = Depends(verify_access_token),
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

    Admin/Staff: always granted (RLS policy handles data).
    Client roles: must have company_id in their JWT company_ids list.

    Usage:
        @router.get("/companies/{company_id}/compliance")
        async def get_compliance(
            company_id: UUID,
            _: str = Depends(require_company_access()),
            token: TokenData = Depends(verify_access_token),
        ):
    """
    def _check_access(
        company_id: uuid.UUID,
        token: TokenData = Depends(verify_access_token),
    ) -> uuid.UUID:
        # Admin/Staff/Legal: bypass — RLS handles DB-level isolation
        if token.role in (
            UserRole.SUPER_ADMIN,
            UserRole.ADMIN_STAFF,
            UserRole.LEGAL_STAFF,
        ):
            return company_id

        # Client roles: must have this company in their JWT
        company_str = str(company_id)
        if company_str not in token.company_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this company.",
            )
        return company_id

    return _check_access


def get_client_company_filter(
    token: TokenData = Depends(verify_access_token),
) -> Optional[List[str]]:
    """
    For list endpoints: return the company_ids filter for client roles.
    Admin/Staff get None (no filter = all companies via RLS).
    Client roles get their JWT company_ids list as the filter.
    """
    if token.is_admin or token.is_legal_staff:
        return None  # No filter — RLS handles it
    return token.company_ids


# ═══════════════════════════════════════════════════════════════════════
# REVENUE / ADMIN-ONLY GUARD
# ═══════════════════════════════════════════════════════════════════════

def require_revenue_access(
    token: TokenData = Depends(verify_access_token),
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
# RULE ENGINE SINGLETON
# ═══════════════════════════════════════════════════════════════════════

_rule_engine_instance = None


def get_rule_engine():
    """
    Return singleton NLCRuleEngine instance.
    Engine is loaded once at startup (deterministic, no state between calls).
    AI Constitution Article 1: Rule engine is immutable during runtime.
    Modifying rules in DB does NOT hot-reload the engine — requires restart.
    """
    global _rule_engine_instance
    if _rule_engine_instance is None:
        # Import here to avoid circular imports at module load time
        from C_rule_engine import NLCRuleEngine
        _rule_engine_instance = NLCRuleEngine()
    return _rule_engine_instance


# ═══════════════════════════════════════════════════════════════════════
# ANNOTATED SHORTHAND TYPES
# (Use in function signatures for cleaner code)
# ═══════════════════════════════════════════════════════════════════════

# Type aliases for common dependencies
DBSession    = Annotated[AsyncSession, Depends(get_db)]
AdminDB      = Annotated[AsyncSession, Depends(get_admin_db)]
CurrentToken = Annotated[TokenData, Depends(verify_access_token)]
CurrentUser  = Annotated[User, Depends(get_current_user)]
Pagination   = Annotated[PaginationParams, Depends(get_pagination)]
RequestID    = Annotated[str, Depends(get_request_id)]
AppSettings  = Annotated[Settings, Depends(get_settings)]
AdminAccess  = Annotated[TokenData, Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF))]
SuperAdmin   = Annotated[TokenData, Depends(require_roles(UserRole.SUPER_ADMIN))]
StaffAccess  = Annotated[TokenData, Depends(require_roles(
    UserRole.SUPER_ADMIN, UserRole.ADMIN_STAFF, UserRole.LEGAL_STAFF
))]
RevenueAccess = Annotated[TokenData, Depends(require_revenue_access)]
