"""
NEUM LEX COUNSEL — ORM LAYER
database.py — Async SQLAlchemy engine, session factory, Base declaration
All DB interactions are async (asyncpg driver).
AES-256 encryption at rest enforced at PostgreSQL/AWS layer.
TLS 1.3 enforced in connection string.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

from fastapi import HTTPException, Request
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
_REQUIRE_RLS_APP_ROLE = os.environ.get(
    "REQUIRE_RLS_APP_ROLE", "true" if _ENVIRONMENT in {"prod", "production"} else "false"
).strip().lower() == "true""

if _REQUIRE_RLS_APP_ROLE and not _APP_DATABASE_URL:
    raise RuntimeError(
        "APP_DATABASE_URL is required when REQUIRE_RLS_APP_ROLE=true; "
        "refusing to run the API with a potentially BYPASSRLS migration role."
    )

# AsyncSessionLocal is the runtime application pool. DATABASE_URL remains the
# privileged connection used by Alembic; APP_DATABASE_URL must be a
# non-superuser, NOBYPASSRLS role such as nlc_app_role.
DATABASE_URL = _APP_DATABASE_URL or _MIGRATION_DATABASE_URL
if not DATABASE_URL:
    raise RuntimeError('DATABASE_URL or APP_DATABASE_URL is empty; refusing to start')
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# ── CONNECTION ────────────────────────────────────────────────────────
_testing = os.environ.get("TESTING", "false").lower() == "true"

engine_args = {
    "echo": os.environ.get("SQL_ECHO", "false").lower() == "true",
    "pool_pre_ping": True,
    "pool_recycle": 3600,
    "connect_args": {
        "server_settings": {
            "application_name": "nlc_api",
            "timezone": "UTC",
        }
    },
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

    user_id = "ANONYMOUS"
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        payload = decode_token(auth_header[7:])
        if payload and payload.get("type") == "access":
            user_id = payload.get("sub") or payload.get("user_id") or "ANONYMOUS"

    async with AsyncSessionLocal() as session:
        try:
            await set_rls_context(session, user_id)
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
                    "SELECT current_user, rolsuper, rolbypassrls "
                    "FROM pg_roles WHERE rolname = current_user"
                )
            )
        ).one_or_none()
    if row is None:
        raise RuntimeError("Unable to verify runtime PostgreSQL role")
    role_name, is_superuser, bypasses_rls = row
    if role_name != "nlc_app_role" or is_superuser or bypasses_rls:
        raise RuntimeError(
            "Unsafe runtime database role: expected nlc_app_role with "
            "NOSUPERUSER and NOBYPASSRLS"
        )


# ── STARTUP / SHUTDOWN ────────────────────────────────────────────────
async def create_tables() -> None:
    """Create all tables. Used in testing only. Production uses Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the database engine cleanly."""
    await engine.dispose()
