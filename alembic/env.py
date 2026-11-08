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

IMPORTANT: All 29 ORM models must be imported below so Alembic
           can detect them during autogenerate. They are imported
           via 'from app.models import *' through Base.metadata.
"""
import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
import alembic.ddl.impl as alembic_ddl_impl
from alembic.ddl.postgresql import PostgresqlImpl
from sqlalchemy import (
    Column,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    pool,
    text,
)
from sqlalchemy.engine import Connection, make_url
from sqlalchemy.ext.asyncio import async_engine_from_config


class NLCPostgresqlImpl(PostgresqlImpl):
    """Use a 255-character Alembic revision column for NLC migrations."""

    def version_table_impl(
        self,
        *,
        version_table,
        version_table_schema,
        version_table_pk,
        **kw,
    ):
        table = Table(
            version_table,
            MetaData(),
            Column("version_num", String(255), nullable=False),
            schema=version_table_schema,
        )
        if version_table_pk:
            table.append_constraint(
                PrimaryKeyConstraint(
                    "version_num",
                    name=f"{version_table}_pkc",
                )
            )
        return table


# Alembic 1.20.0 resolves implementations through this module-level registry.
# This affects only this Alembic process; it does not alter the database.
if alembic_ddl_impl._impls.get("postgresql") is PostgresqlImpl:
    alembic_ddl_impl._impls["postgresql"] = NLCPostgresqlImpl
elif alembic_ddl_impl._impls.get("postgresql") is not NLCPostgresqlImpl:
    raise RuntimeError(
        "Unexpected Alembic PostgreSQL implementation; "
        "refusing to replace another custom implementation."
    )

# ── Path Setup ───────────────────────────────────────────────────────
# Ensure project root is on sys.path so app.models can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Load project .env before importing app.models.
# Existing shell environment variables always take precedence.
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env", override=False)

# ── Import ALL models so Alembic sees them in metadata ────────────────
# This is critical for autogenerate — every model must be imported here
from app.models import (  # noqa: F401 — imports are for side-effects
    AGM,
    AIOutputLog,
    AIPromptTemplate,
    AnnualReturn,
    Audit,
    Base,
    Company,
    CompanyCharge,
    CompanyUserAccess,
    ComplianceEvent,
    ComplianceFlag,
    ComplianceScoreHistory,
    Director,
    Document,
    DocumentAccessLog,
    Engagement,
    LegalRule,
    LegalRuleVersion,
    Notification,
    Quotation,
    RegisteredOfficeHistory,
    RescuePlan,
    RescueStep,
    Shareholder,
    ShareTransfer,
    SRORegistry,
    StatutoryRegister,
    Task,
    User,
    UserActivityLog,
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
    Include: All 29 tables in public schema.
    """
    if type_ == "table" and name.startswith("vw_"):
        # Views are created via raw SQL in migrations, not ORM
        return False
    return not (type_ == "schema" and name not in (None, "public"))


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


def validate_production_migration_role(connection: Connection) -> None:
    """Fail before DDL if Render is using the restricted runtime DB role.

    Production migrations need the privileged owner connection. The API uses
    APP_DATABASE_URL as nlc_app_role; Alembic must use DATABASE_URL as the
    migration/owner principal.
    """
    """Fail before DDL if a production deployment uses the restricted runtime role.

    Render sets RENDER=true. Other production hosts must explicitly set
    ENVIRONMENT=production. Local development and CI do not run this gate.
    """
    is_render = os.environ.get("RENDER", "").strip().lower() == "true"
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    if not (is_render or environment in {"prod", "production"}):
        return

    row = connection.execute(
        text(
            """
            SELECT current_user,
                   r.rolsuper,
                   r.rolbypassrls,
                   CASE
                       WHEN audit_table.oid IS NULL THEN NULL
                       ELSE audit_table.relowner = r.oid
                   END AS owns_rescue_audit_log
              FROM pg_roles AS r
              LEFT JOIN pg_class AS audit_table
                ON audit_table.oid = to_regclass('public.rescue_audit_log')
             WHERE r.rolname = current_user
            """
        )
    ).one_or_none()

    if row is None:
        raise RuntimeError("Unable to inspect the PostgreSQL migration role.")

    role_name, is_superuser, bypasses_rls, owns_rescue_audit_log = row
    if role_name == "nlc_app_role":
        raise RuntimeError(
            "DATABASE_URL is using nlc_app_role. Set DATABASE_URL to the "
            "privileged migration/table-owner connection; keep APP_DATABASE_URL "
            "as the restricted nlc_app_role runtime connection."
        )
    if not (is_superuser or bypasses_rls):
        raise RuntimeError(
            f"Migration role {role_name!r} must have BYPASSRLS or SUPERUSER "
            "for the signed-RLS migrations; use the provisioned migration owner."
        )
    if owns_rescue_audit_log is False and not is_superuser:
        raise RuntimeError(
            f"Migration role {role_name!r} does not own public.rescue_audit_log. "
            "Use the database owner connection; do not grant ownership to nlc_app_role."
        )


async def run_async_migrations() -> None:
    """
    Async entry point for migrations.
    Uses asyncpg engine with NullPool for Alembic (one connection per run).
    """
    from app.core.db_url import normalize_asyncpg_url

    # Override URL with resolved value. Render/production always require
    # certificate-verified TLS, even when the provider URL omits sslmode.
    configuration = config.get_section(config.config_ini_section, {})
    is_render = os.environ.get("RENDER", "").strip().lower() == "true"
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    require_tls = is_render or environment in {"prod", "production"}
    db_url, ssl_context = normalize_asyncpg_url(
        get_database_url(),
        require_tls=require_tls,
    )
    connect_args = {}
    if ssl_context is not None:
        connect_args["ssl"] = ssl_context
    import ssl as _ssl

    # Override URL with resolved value. asyncpg uses connect_args["ssl"],
    # not libpq's sslmode URL parameter. Require verified TLS on Render and
    # production hosts even when the operator omitted sslmode=require.
    configuration = config.get_section(config.config_ini_section, {})
    db_url = get_database_url()
    parsed_url = make_url(db_url)
    sslmode = str(parsed_url.query.get("sslmode", "")).lower()
    ssl_option = str(parsed_url.query.get("ssl", "")).lower()
    is_render = os.environ.get("RENDER", "").strip().lower() == "true"
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    is_production = is_render or environment in {"prod", "production"}

    if is_production and sslmode in {"disable", "allow", "prefer"}:
        raise RuntimeError(
            "PostgreSQL TLS must be required for production migrations; "
            "remove the insecure sslmode and use a verified TLS connection."
        )

    require_tls = (
        is_production
        or sslmode in {"require", "verify-ca", "verify-full"}
        or ssl_option in {"true", "1", "require"}
    )
    db_url = parsed_url.difference_update_query(["sslmode", "ssl"]).render_as_string(
        hide_password=False
    )
    connect_args = {}
    if require_tls:
        connect_args["ssl"] = _ssl.create_default_context()

    configuration["sqlalchemy.url"] = db_url

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Always NullPool for migrations
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        # SET starts an implicit SQLAlchemy transaction. Commit it before
        # handing the connection to Alembic, otherwise Alembic's
        # transaction_per_migration and autocommit boundaries are not owned
        # by its MigrationContext.
        await connection.execute(text("SET timezone = 'UTC'"))
        await connection.commit()
        await connection.run_sync(validate_production_migration_role)
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    """Online mode entry point — runs async loop."""
    asyncio.run(run_async_migrations())


# ── ENTRY POINT ───────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
