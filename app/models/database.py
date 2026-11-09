"""
NEUM LEX COUNSEL — ORM LAYER
database.py — Async SQLAlchemy engine, session factory, Base declaration
All DB interactions are async (asyncpg driver).
AES-256 encryption at rest enforced at PostgreSQL/AWS layer.
TLS is enforced through verified asyncpg SSL contexts in production.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request

from app.db_url import is_render_runtime, normalize_asyncpg_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ══════════════════════════════════════════════════════════════════════
# CRITICAL FIX: Use settings to auto-convert postgres:// to postgresql+asyncpg://
# Render injects postgres:// but asyncpg requires postgresql+asyncpg://
# ══════════════════════════════════════════════════════════════════════
_APP_DATABASE_URL = os.environ.get("APP_DATABASE_URL", "").strip()
_MIGRATION_DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
_ENVIRONMENT = os.environ.get("ENVIRONMENT", "development").strip().lower()
# Render always injects RENDER=true. Treat every Render runtime (including
# preview/staging services) as deployment-grade: never silently fall back to
# the privileged migration URL because ENVIRONMENT was omitted or mistyped.
_RENDER_RUNTIME = is_render_runtime(os.environ)
_PRODUCTION_ENVIRONMENT = _ENVIRONMENT in {"prod", "production"} or _RENDER_RUNTIME
_RLS_ROLE_SETTING = os.environ.get("REQUIRE_RLS_APP_ROLE")
if _PRODUCTION_ENVIRONMENT:
    # A deployment operator must not be able to disable the runtime-role
    # boundary with an environment override and silently fall back to the
    # privileged migration URL.
    if _RLS_ROLE_SETTING is not None and _RLS_ROLE_SETTING.strip().lower() != "true":
        raise RuntimeError(
            "REQUIRE_RLS_APP_ROLE cannot be disabled in production; "
            "the API must use APP_DATABASE_URL as nlc_app_role."
        )
    _REQUIRE_RLS_APP_ROLE = True
else:
    _REQUIRE_RLS_APP_ROLE = (
        (_RLS_ROLE_SETTING or "false").strip().lower() == "true"
    )

if _REQUIRE_RLS_APP_ROLE and not _APP_DATABASE_URL:
    raise RuntimeError(
        "APP_DATABASE_URL is required when REQUIRE_RLS_APP_ROLE=true; "
        "refusing to run the API with a potentially BYPASSRLS migration role."
    )

if _PRODUCTION_ENVIRONMENT and len(os.environ.get("NLC_RLS_HMAC_SECRET", "")) < 32:
    raise RuntimeError(
        "NLC_RLS_HMAC_SECRET must contain at least 32 characters in production/Render"
    )

# AsyncSessionLocal is the runtime application pool. DATABASE_URL remains the
# privileged connection used by Alembic; APP_DATABASE_URL must be a
# non-superuser, NOBYPASSRLS role such as nlc_app_role.
DATABASE_URL = _APP_DATABASE_URL or _MIGRATION_DATABASE_URL
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL or APP_DATABASE_URL is empty; refusing to start')

DATABASE_URL, _DATABASE_SSL_CONTEXT = normalize_asyncpg_url(
    DATABASE_URL,
    require_tls=_PRODUCTION_ENVIRONMENT,
)

# ── CONNECTION ────────────────────────────────────────────────────────
_testing = os.environ.get("TESTING", "false").lower() == "true"

_connect_args: dict[str, Any] = {
    "server_settings": {
        "application_name": "nlc_api",
        "timezone": "UTC",
    }
}
if _DATABASE_SSL_CONTEXT is not None:
    _connect_args["ssl"] = _DATABASE_SSL_CONTEXT

engine_args: dict[str, Any] = {
    "echo": os.environ.get("SQL_ECHO", "false").lower() == "true",
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "connect_args": _connect_args,
}

if not _testing:
    engine_args.update({
        "pool_size": int(os.environ.get("DB_POOL_SIZE", "20")),
        "max_overflow": int(os.environ.get("DB_MAX_OVERFLOW", "40")),
    })
else:
    engine_args["poolclass"] = NullPool

engine = create_async_engine(DATABASE_URL, **engine_args)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── BASE ──────────────────────────────────────────────────────────────
class Base(AsyncAttrs, DeclarativeBase):
    """
    Declarative base for all ORM models.
    AsyncAttrs enables async lazy-loading of relationships.
    """
    pass


# ── SESSION DEPENDENCY ────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency. Yields a database session.
    Rolls back on exception. Always closes.

    Usage:
        @router.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            ...
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




async def get_db_for_user(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency: session with RLS context for the authenticated user.
    Extracts user_id from JWT Bearer token. Falls back to ANONYMOUS.
    """
    from app.core.security import decode_token

    principal = "ANONYMOUS"
    auth_header = request.headers.get("authorization", "")
    if auth_header:
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid authorization header")
        payload = decode_token(auth_header[7:], expected_type="access")
        jti = payload.get("jti") if payload else None
        if not payload or not isinstance(jti, str) or not jti:
            raise HTTPException(status_code=401, detail="Invalid or expired access token")
        from starlette.concurrency import run_in_threadpool
        from app.core.token_blacklist import BlacklistUnavailable, is_revoked
        try:
            if await run_in_threadpool(is_revoked, jti, fail_closed=True):
                raise HTTPException(status_code=401, detail="Token has been revoked")
        except BlacklistUnavailable as exc:
            raise HTTPException(status_code=503, detail="Authentication service temporarily unavailable") from exc
        principal = payload.get("sub") or payload.get("user_id") or ""
        if not principal:
            raise HTTPException(status_code=401, detail="Access token has no user identity")

    async with AsyncSessionLocal() as session:
        try:
            if principal == "ANONYMOUS":
                await _set_signed_rls_principal(session, principal)
            else:
                await set_rls_context(session, principal)
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── ROW-LEVEL SECURITY ────────────────────────────────────────────────
def _rls_signature(principal: str) -> str:
    """Return the HMAC proof for a transaction-local RLS principal."""
    import hashlib
    import hmac

    secret = os.environ.get("NLC_RLS_HMAC_SECRET", "")
    if len(secret) < 32:
        raise RuntimeError(
            "NLC_RLS_HMAC_SECRET must contain at least 32 characters for signed RLS identity"
        )
    return hmac.new(
        secret.encode("utf-8"),
        principal.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


async def set_app_role(session: AsyncSession) -> None:
    """Run application queries as the non-owner, non-BYPASSRLS database role."""
    await session.execute(text("SET LOCAL ROLE nlc_app_role"))


async def _set_signed_rls_principal(session: AsyncSession, principal: str) -> None:
    await set_app_role(session)
    signature = _rls_signature(principal)
    await session.execute(
        text(
            "SELECT set_config('app.current_user_id', :uid, true), "
            "set_config('app.current_user_signature', :signature, true)"
        ),
        {"uid": principal, "signature": signature},
    )


async def set_rls_context(session: AsyncSession, user_id: str) -> None:
    """Set a signed UUID identity; malformed or non-UUID callers fail closed."""
    import uuid

    try:
        principal = str(uuid.UUID(str(user_id)))
    except (TypeError, ValueError, AttributeError) as exc:
        raise ValueError("RLS user identity must be a valid UUID") from exc
    await _set_signed_rls_principal(session, principal)


async def set_admin_context(session: AsyncSession) -> None:
    """Set the signed service principal for trusted background/admin work."""
    await _set_signed_rls_principal(session, "ADMIN")


async def set_auth_context(session: AsyncSession) -> None:
    """Set the signed, narrowly-scoped authentication service principal."""
    await _set_signed_rls_principal(session, "AUTH")


async def set_catalog_context(session: AsyncSession) -> None:
    """Set the signed, read-only public-catalogue service principal."""
    await _set_signed_rls_principal(session, "CATALOG")


async def verify_runtime_database_role() -> None:
    """Fail startup if production is connected through an owner/BYPASSRLS role."""
    if not _REQUIRE_RLS_APP_ROLE:
        return
    async with engine.connect() as connection:
        row = (
            await connection.execute(
                text(
                    "SELECT current_user, rolsuper, rolcreatedb, rolcreaterole, "
                    "rolinherit, rolreplication, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            )
        ).one_or_none()
        if row is None:
            raise RuntimeError("Unable to verify runtime PostgreSQL role")
        (
            role_name,
            is_superuser,
            can_create_db,
            can_create_role,
            inherits_roles,
            can_replicate,
            bypasses_rls,
        ) = row
        memberships: bool = (
            await connection.execute(
                text(
                    "SELECT EXISTS ("
                    "SELECT 1 FROM pg_auth_members m "
                    "JOIN pg_roles granted_role ON granted_role.oid = m.roleid "
                    "JOIN pg_roles member_role ON member_role.oid = m.member "
                    "JOIN pg_roles grantor_role ON grantor_role.oid = m.grantor "
                    "WHERE (member_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role') "
                    "OR granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')) "
                    "AND NOT ("
                    "member_role.rolname = 'neondb_owner' "
                    "AND granted_role.rolname IN ('nlc_app_role', 'nlc_ci_audit_role') "
                    "AND grantor_role.rolname = 'cloud_admin' "
                    "AND m.admin_option IS TRUE "
                    "AND m.inherit_option IS FALSE "
                    "AND m.set_option IS FALSE)"
                    ")"                )
            )
        ).scalar_one()

    if (
        role_name != "nlc_app_role"
        or is_superuser
        or can_create_db
        or can_create_role
        or inherits_roles
        or can_replicate
        or bypasses_rls
        or memberships
    ):
        raise RuntimeError(
            "Unsafe runtime database role: expected nlc_app_role with "
            "NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, "
            "NOREPLICATION, NOBYPASSRLS, no inherited memberships, and no grants to untrusted roles"
        )

    # Prove that the runtime secret matches the database's private signing key.
    # This uses a synthetic UUID inside a transaction and rolls it back; the
    # API must not become healthy with a mismatched secret that makes every
    # authenticated RLS query silently fail closed.
    principal = "00000000-0000-0000-0000-000000000001"
    async with engine.connect() as connection:
        await connection.execute(
            text(
                "SELECT set_config('app.current_user_id', :uid, true), "
                "set_config('app.current_user_signature', :signature, true)"
            ),
            {"uid": principal, "signature": _rls_signature(principal)},
        )
        verified_principal = (
            await connection.execute(
                text("SELECT public.nlc_current_user_principal()")
            )
        ).scalar_one_or_none()
        await connection.rollback()

    if verified_principal != principal:
        raise RuntimeError(
            "NLC_RLS_HMAC_SECRET does not match the database signing key; "
            "refusing to start the runtime API"
        )


# ── STARTUP / SHUTDOWN ────────────────────────────────────────────────
async def create_tables() -> None:
    """Create all tables. Used in testing only. Production uses Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the database engine cleanly."""
    await engine.dispose()
