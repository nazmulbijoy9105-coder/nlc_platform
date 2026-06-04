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

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncAttrs,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from fastapi import Request

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

# ══════════════════════════════════════════════════════════════════════
# CRITICAL FIX: Use settings to auto-convert postgres:// to postgresql+asyncpg://
# Render injects postgres:// but asyncpg requires postgresql+asyncpg://
# ══════════════════════════════════════════════════════════════════════
DATABASE_URL = os.environ.get('DATABASE_URL', '')
if DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql+asyncpg://', 1)
elif DATABASE_URL.startswith('postgresql://'):
    DATABASE_URL = DATABASE_URL.replace('postgresql://', 'postgresql+asyncpg://', 1)

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
async def set_rls_context(session: AsyncSession, user_id: str) -> None:
    """
    Set PostgreSQL session variable for Row-Level Security.
    Called after JWT validation, before any company data query.
    RLS policies in schema check: current_setting('app.current_user_id').
    """
    await session.execute(
        text("SELECT set_config('app.current_user_id', :uid, true)"),
        {"uid": str(user_id)},
    )


async def set_admin_context(session: AsyncSession) -> None:
    """
    Bypass RLS for Super Admin and background jobs.
    Only used for: cron jobs, rule engine evaluation, seeder scripts.
    AI Constitution Article 2: Admin context is audited separately.
    """
    await session.execute(
        text("SELECT set_config('app.current_user_id', 'ADMIN', true)")
    )


# ── STARTUP / SHUTDOWN ────────────────────────────────────────────────
async def create_tables() -> None:
    """Create all tables. Used in testing only. Production uses Alembic."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def dispose_engine() -> None:
    """Dispose of the database engine cleanly."""
    await engine.dispose()
