"""
NEUM LEX COUNSEL — Alembic Environment
alembic/env.py

Async-aware Alembic environment using SQLAlchemy 2.0 + asyncpg.
Reads DATABASE_URL from environment (never from alembic.ini).
Handles PostgreSQL ENUMs, RLS, and triggers correctly.

How it works:
  - Online mode (alembic upgrade/downgrade): uses async engine
  - Offline mode (--sql flag): generates raw SQL for review
  - autogenerate: compares ORM models to current DB state

IMPORTANT: All 28 ORM models must be imported below so Alembic
           can detect them during autogenerate. They are imported
           via 'from app.models import *' through Base.metadata.
"""
import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ── Path Setup ───────────────────────────────────────────────────────
# Ensure project root is on sys.path so app.models can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ── Import ALL models so Alembic sees them in metadata ────────────────
# This is critical for autogenerate — every model must be imported here
from app.models import (  # noqa: F401 — imports are for side-effects
    Base,
    User, Company, CompanyUserAccess,
    Director, Shareholder, ShareTransfer,
    AGM, Audit, AnnualReturn,
    ComplianceFlag, ComplianceScoreHistory, ComplianceEvent,
    LegalRule, LegalRuleVersion,
    RescuePlan, RescueStep,
    Task, Engagement, Quotation,
    Document, DocumentAccessLog, AIPromptTemplate, AIOutputLog,
    Notification, SRORegistry, StatutoryRegister,
    RegisteredOfficeHistory, UserActivityLog,
)

# ── Alembic Config ────────────────────────────────────────────────────
config = context.config
target_metadata = Base.metadata

# Logging configuration from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Database URL ──────────────────────────────────────────────────────
# Read from environment — never hardcode credentials
def get_database_url() -> str:
    """
    Resolve DATABASE_URL from environment.
    Converts postgres:// → postgresql+asyncpg:// for async engine.
    """
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        # Try loading from .env file
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not url:
        raise RuntimeError(
            "DATABASE_URL environment variable not set. "
            "Copy .env.template to .env and fill in credentials."
        )

    # Ensure asyncpg driver for async operations
    if url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)

    return url


# ── Autogenerate Configuration ────────────────────────────────────────
def include_object(object, name, type_, reflected, compare_to):
    """
    Control what Alembic includes in autogenerate diff.
    Exclude: PostgreSQL system schemas, views (managed in migrations directly).
    Include: All 28 tables in public schema.
    """
    if type_ == "table" and name.startswith("vw_"):
        # Views are created via raw SQL in migrations, not ORM
        return False
    if type_ == "schema" and name not in (None, "public"):
        return False
    return True


def compare_type(context, inspected_column, metadata_column, inspected_type, metadata_type):
    """
    More precise type comparison — prevents unnecessary migrations
    for types that are functionally equivalent.
    """
    return None  # Use Alembic default comparison


# ── OFFLINE MODE ──────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Offline mode: generate SQL script without DB connection.
    Used for: reviewing migrations before deployment, CI/CD checks.
    
    Run: alembic upgrade head --sql > migration.sql
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        # Include PostgreSQL-specific features
        render_as_batch=False,
        transaction_per_migration=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── ONLINE MODE (ASYNC) ───────────────────────────────────────────────
def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations using live connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_object=include_object,
        compare_type=True,
        compare_server_default=True,
        transaction_per_migration=True,
        # Alembic will create/drop enums correctly
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Async entry point for migrations.
    Uses asyncpg engine with NullPool for Alembic (one connection per run).
    """
    # Override URL with resolved value
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Always NullPool for migrations
    )

    async with connectable.connect() as connection:
        # Set timezone for the session
        await connection.execute(text("SET timezone = 'UTC'"))
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online mode entry point — runs async loop."""
    asyncio.run(run_async_migrations())


# ── ENTRY POINT ───────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
