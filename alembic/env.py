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
    inspect,
    pool,
    text,
)
from sqlalchemy.engine import Connection
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

from app.db_url import is_render_runtime, prepare_asyncpg_connection

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
    CompanyFact,
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
    RescueAuditLog,
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
def _is_production_migration_environment() -> bool:
    return is_render_runtime(os.environ) or os.environ.get(
        "ENVIRONMENT", ""
    ).strip().lower() in {"prod", "production"}


def get_database_url() -> str:
    """
    Resolve the dedicated migration connection URL.

    Production and Render must use MIGRATION_DATABASE_URL explicitly. Never
    fall back to DATABASE_URL there: that name may point to the restricted
    application connection or an unverified owner credential.
    """
    is_production = _is_production_migration_environment()
    migration_url = os.environ.get("MIGRATION_DATABASE_URL", "").strip()

    if is_production and not migration_url:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL is required in production/Render. "
            "DATABASE_URL fallback is disabled for migrations; configure an "
            "explicit, reviewed migration-login connection."
        )

    url = migration_url or os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "MIGRATION_DATABASE_URL or DATABASE_URL environment variable not set."
        )

    # Ensure asyncpg driver for async operations.
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
def ensure_alembic_version_column_capacity(connection: Connection) -> None:
    """Widen an existing Alembic version column before long revision IDs are written.

    version_table_impl controls only newly-created version tables. Databases
    upgraded from older releases may still have VARCHAR(32), which cannot store
    current revision identifiers. This additive, idempotent preflight preserves
    the existing revision value and is committed before migration execution.
    """
    inspector = inspect(connection)
    if not inspector.has_table("alembic_version"):
        return

    columns = {
        column["name"]: column["type"]
        for column in inspector.get_columns("alembic_version")
    }
    version_type = columns.get("version_num")
    if version_type is None:
        raise RuntimeError(
            "Existing alembic_version table has no version_num column; "
            "refusing to run migrations."
        )

    current_length = getattr(version_type, "length", None)
    if current_length is not None and current_length < 255:
        connection.execute(
            text(
                "ALTER TABLE alembic_version "
                "ALTER COLUMN version_num TYPE VARCHAR(255)"
            )
        )


def preflight_historical_evidence_schema(connection: Connection) -> None:
    """Stop a restored 0042 branch before migration 0044 can synthesize empty tables."""
    version_table = connection.execute(
        text("SELECT to_regclass('public.alembic_version')")
    ).scalar_one_or_none()
    if version_table is None:
        # A fresh database has no Alembic state yet; 0037/0038 will create
        # these tables as part of the ordinary forward migration chain.
        return

    revisions = set(
        connection.execute(
            text("SELECT version_num FROM public.alembic_version")
        ).scalars().all()
    )
    guarded_revisions = {
        "0042_dedup_key",
        "0043_reconcile_notification_dedup_key",
        "b10c91ac6860",
    }
    if not revisions.intersection(guarded_revisions):
        return

    expected_columns = {
        "webhook_endpoints": {
            "id", "user_id", "url", "secret", "events", "is_active",
            "last_delivery_at", "last_response_code", "created_at", "updated_at",
        },
        "webhook_deliveries": {
            "id", "endpoint_id", "event_type", "payload", "status", "attempts",
            "max_attempts", "response_code", "response_body", "error_message",
            "delivered_at", "next_retry_at", "created_at",
        },
        "rescue_audit_log": {
            "id", "rescue_plan_id", "finding_id", "rule_id", "rule_version",
            "action_performed", "actor_user_id", "evidence_ref", "outcome",
            "notes", "created_at", "updated_at",
        },
    }
    missing_tables: list[str] = []
    missing_columns: dict[str, list[str]] = {}

    for table_name, required_columns in expected_columns.items():
        exists = connection.execute(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                      FROM pg_class AS c
                      JOIN pg_namespace AS n ON n.oid = c.relnamespace
                     WHERE n.nspname = 'public'
                       AND c.relname = :table_name
                       AND c.relkind IN ('r', 'p')
                )
                """
            ),
            {"table_name": table_name},
        ).scalar_one()
        if not exists:
            missing_tables.append(table_name)
            continue

        actual_columns = set(
            connection.execute(
                text(
                    """
                    SELECT column_name
                      FROM information_schema.columns
                     WHERE table_schema = 'public'
                       AND table_name = :table_name
                    """
                ),
                {"table_name": table_name},
            ).scalars().all()
        )
        absent = sorted(required_columns - actual_columns)
        if absent:
            missing_columns[table_name] = absent

    if missing_tables or missing_columns:
        raise RuntimeError(
            "Refusing Alembic execution before 0044_webhook_schema_reconcile: "
            "the applied 0042/0043/b10c91ac6860 revision marker requires the "
            "0037/0038 webhook and rescue-audit schema to be present and "
            "reconciled. Migration 0044 can create schema-only replacements "
            "but cannot recover historical rows. "
            f"Missing tables={sorted(missing_tables)!r}; "
            f"missing columns={missing_columns!r}. "
            "Recover and verify the original schema/evidence, or complete a "
            "separately approved schema-only reconstruction before retrying."
        )


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


def prepare_production_migration_role(connection: Connection) -> None:
    """Assume the non-login schema-owner role through a least-privilege login.

    The login principal must be nlc_migration_user (NOINHERIT and without
    BYPASSRLS/CREATEDB/CREATEROLE). It may SET ROLE only to the non-login
    nlc_migration_owner group, which owns migration-managed objects and has
    BYPASSRLS for the SECURITY DEFINER RLS helpers.
    """
    if not _is_production_migration_environment():
        return

    session_user, current_user, server_version = connection.execute(
        text(
            "SELECT session_user, current_user, "
            "current_setting('server_version_num')::int"
        )
    ).one()

    if session_user != "nlc_migration_user" or current_user != session_user:
        raise RuntimeError(
            "Production migrations must connect as session_user "
            "'nlc_migration_user' before assuming 'nlc_migration_owner'; "
            f"observed session_user={session_user!r}, current_user={current_user!r}."
        )
    if server_version < 160000:
        raise RuntimeError(
            "The controlled migration-role membership contract requires "
            "PostgreSQL 16+ SET/INHERIT membership options."
        )

    login_role = connection.execute(
        text(
            """
            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                   rolinherit, rolreplication, rolbypassrls
              FROM pg_roles
             WHERE rolname = 'nlc_migration_user'
            """
        )
    ).one_or_none()
    if login_role is None or tuple(login_role) != (
        True, False, False, False, False, False, False
    ):
        raise RuntimeError(
            "nlc_migration_user must be LOGIN, NOSUPERUSER, NOCREATEDB, "
            "NOCREATEROLE, NOINHERIT, NOREPLICATION and NOBYPASSRLS."
        )

    owner_role = connection.execute(
        text(
            """
            SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                   rolinherit, rolreplication, rolbypassrls
              FROM pg_roles
             WHERE rolname = 'nlc_migration_owner'
            """
        )
    ).one_or_none()
    if owner_role is None or tuple(owner_role) != (
        False, False, False, False, False, False, True
    ):
        raise RuntimeError(
            "nlc_migration_owner must be NOLOGIN, NOSUPERUSER, NOCREATEDB, "
            "NOCREATEROLE, NOINHERIT, NOREPLICATION and BYPASSRLS."
        )

    membership = connection.execute(
        text(
            """
            SELECT admin_option, inherit_option, set_option
              FROM pg_auth_members
             WHERE member = (SELECT oid FROM pg_roles WHERE rolname = session_user)
               AND roleid = (SELECT oid FROM pg_roles WHERE rolname = 'nlc_migration_owner')
            """
        )
    ).one_or_none()
    if membership is None or tuple(membership) != (False, False, True):
        raise RuntimeError(
            "nlc_migration_user must have only a non-inheriting, non-admin "
            "SET ROLE membership in nlc_migration_owner."
        )

    connection.execute(text("SET ROLE nlc_migration_owner"))
    assumed_role = connection.execute(text("SELECT current_user")).scalar_one()
    if assumed_role != "nlc_migration_owner":
        raise RuntimeError(
            "Unable to assume the controlled nlc_migration_owner role."
        )


def validate_production_migration_role(connection: Connection) -> None:
    """Fail before DDL unless the controlled migration owner is active."""
    if not _is_production_migration_environment():
        return

    row = connection.execute(
        text(
            """
            SELECT session_user,
                   current_user,
                   r.rolsuper,
                   r.rolbypassrls,
                   CASE
                       WHEN audit_table.oid IS NULL THEN NULL
                       ELSE audit_table.relowner = r.oid
                   END AS owns_rescue_audit_log,
                   version_table.relowner = r.oid AS owns_alembic_version,
                   has_database_privilege(r.oid, current_database(), 'CREATE')
                       AS can_create_in_database,
                   has_schema_privilege(r.oid, 'public', 'CREATE')
                       AS can_create_in_public
              FROM pg_roles AS r
              LEFT JOIN pg_class AS audit_table
                ON audit_table.oid = to_regclass('public.rescue_audit_log')
              JOIN pg_class AS version_table
                ON version_table.oid = to_regclass('public.alembic_version')
             WHERE r.rolname = current_user
            """
        )
    ).one_or_none()

    if row is None:
        raise RuntimeError("Unable to inspect the PostgreSQL migration role.")

    (
        login_name,
        role_name,
        is_superuser,
        bypasses_rls,
        owns_rescue_audit_log,
        owns_alembic_version,
        can_create_in_database,
        can_create_in_public,
    ) = row

    if login_name != "nlc_migration_user" or role_name != "nlc_migration_owner":
        raise RuntimeError(
            "Migration session identity mismatch: require login "
            "nlc_migration_user with current_user nlc_migration_owner; "
            f"observed session_user={login_name!r}, current_user={role_name!r}."
        )
    if is_superuser or not bypasses_rls:
        raise RuntimeError(
            "nlc_migration_owner must be non-superuser and BYPASSRLS; "
            "the LOGIN principal itself must remain NOBYPASSRLS."
        )
    if owns_rescue_audit_log is False:
        raise RuntimeError(
    if role_name == "nlc_app_role":
        raise RuntimeError(
            "DATABASE_URL is using nlc_app_role. Configure the dedicated "
            "nlc_migration_user login and its scoped nlc_migration_owner role; "
            "do not grant ownership to nlc_app_role."
        )
    if login_name != "nlc_migration_user" or role_name != "nlc_migration_owner":
        raise RuntimeError(
            "Migration session identity mismatch: require login "
            "nlc_migration_user with current_user nlc_migration_owner; "
            f"observed session_user={login_name!r}, current_user={role_name!r}."
        )
    if is_superuser or not bypasses_rls:
        raise RuntimeError(
            "nlc_migration_owner must be non-superuser and BYPASSRLS; "
            "the LOGIN principal itself must remain NOBYPASSRLS."
        )
    if owns_rescue_audit_log is False:
        raise RuntimeError(
            "nlc_migration_owner does not own public.rescue_audit_log. "
            "Reconcile object ownership before running migrations."
        )
    if not owns_alembic_version:
        raise RuntimeError(
            "nlc_migration_owner must own public.alembic_version before "
            "Alembic can safely maintain its revision table."
        )
    if not can_create_in_database or not can_create_in_public:
        raise RuntimeError(
            "nlc_migration_owner lacks the reviewed CREATE privileges "
            "required for schema migrations."
        )

    ownership_gaps = connection.execute(
        text(
            """
            SELECT
                (
                    SELECT count(*)
                      FROM pg_class AS c
                      JOIN pg_namespace AS n ON n.oid = c.relnamespace
                     WHERE n.nspname IN ('public', 'nlc_private', 'audit')
                       AND c.relkind IN ('r', 'p', 'v', 'm', 'S', 'f', 'i', 'I')
                       AND c.relowner <> (SELECT oid FROM pg_roles
                                           WHERE rolname = 'nlc_migration_owner')
                ) AS relations,
                (
                    SELECT count(*)
                      FROM pg_proc AS p
                      JOIN pg_namespace AS n ON n.oid = p.pronamespace
                     WHERE n.nspname IN ('public', 'nlc_private', 'audit')
                       AND p.proowner <> (SELECT oid FROM pg_roles
                                           WHERE rolname = 'nlc_migration_owner')
                       AND NOT EXISTS (
                           SELECT 1
                             FROM pg_depend AS d
                            WHERE d.classid = 'pg_proc'::regclass
                              AND d.objid = p.oid
                              AND d.refclassid = 'pg_extension'::regclass
                              AND d.deptype = 'e'
                       )
                ) AS functions,
                (
                    SELECT count(*)
                      FROM pg_type AS t
                      JOIN pg_namespace AS n ON n.oid = t.typnamespace
                     WHERE n.nspname IN ('public', 'nlc_private', 'audit')
                       AND t.typtype IN ('e', 'd', 'c', 'r', 'm')
                       AND t.typowner <> (SELECT oid FROM pg_roles
                                           WHERE rolname = 'nlc_migration_owner')
                       AND NOT EXISTS (
                           SELECT 1
                             FROM pg_depend AS d
                            WHERE d.classid = 'pg_type'::regclass
                              AND d.objid = t.oid
                              AND d.refclassid = 'pg_extension'::regclass
                              AND d.deptype = 'e'
                       )
                ) AS types
            """
        )
    ).one()
    if any(ownership_gaps):
        raise RuntimeError(
            "nlc_migration_owner does not own every migration-managed "
            "relation, function and custom type in public/nlc_private/audit. "
            f"Ownership gaps: relations={ownership_gaps.relations}, "
            f"functions={ownership_gaps.functions}, types={ownership_gaps.types}. "
            "Reconcile ownership before running migrations."
        )

    missing_schema_create = connection.execute(
        text(
            """
            SELECT n.nspname
              FROM pg_namespace AS n
             WHERE n.nspname IN ('public', 'nlc_private', 'audit')
               AND NOT has_schema_privilege(current_user, n.oid, 'CREATE')
             ORDER BY n.nspname
            """
        )
    ).scalars().all()
    if missing_schema_create:
        raise RuntimeError(
            "nlc_migration_owner lacks CREATE on migration schemas: "
            + ", ".join(missing_schema_create)
        )
    ).scalars().all()
    if missing_schema_create:
        raise RuntimeError(
            "nlc_migration_owner lacks CREATE on migration schemas: "
            + ", ".join(missing_schema_create)
        )

    default_delete_grant = connection.execute(
        text(
            """
            SELECT EXISTS (
                SELECT 1
                  FROM pg_default_acl AS d
                  CROSS JOIN LATERAL aclexplode(d.defaclacl) AS acl
                 WHERE d.defaclrole = (
                           SELECT oid FROM pg_roles
                            WHERE rolname = 'nlc_migration_owner'
                       )
                   AND d.defaclobjtype = 'r'
                   AND d.defaclnamespace IN (
                           0,
                           (SELECT oid FROM pg_namespace WHERE nspname = 'public')
                       )
                   AND acl.grantee IN (
                           0,
                           (SELECT oid FROM pg_roles WHERE rolname = 'nlc_app_role')
                       )
                   AND acl.privilege_type = 'DELETE'
            )
            """
        )
    ).scalar_one()
    if default_delete_grant:
        raise RuntimeError(
            "nlc_migration_owner has a global/public default DELETE grant "
            "to PUBLIC or nlc_app_role; revoke it before applying migrations."
        )


async def run_async_migrations() -> None:
    """Run Alembic with the privileged migration URL and verified TLS."""
    configuration = config.get_section(config.config_ini_section, {})
    is_render = is_render_runtime(os.environ)
    environment = os.environ.get("ENVIRONMENT", "").strip().lower()
    require_tls = is_render or environment in {"prod", "production"}

    # Keep Alembic's connection policy explicit and fail closed:
    # strip libpq-only URL parameters, then pass a verified SSLContext through
    # SQLAlchemy's asyncpg connect_args. Neon and Render must never use plaintext.
    db_url, connect_args = prepare_asyncpg_connection(
        get_database_url(),
        require_tls=require_tls,
    )

    configuration["sqlalchemy.url"] = db_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )

    async with connectable.connect() as connection:
        await connection.execute(text("SET timezone = 'UTC'"))
        await connection.commit()
        await connection.run_sync(prepare_production_migration_role)
        await connection.run_sync(validate_production_migration_role)
        # This guard is environment-independent and runs before any Alembic
        # DDL, including the historical 0044 schema-only reconstruction.
        await connection.run_sync(preflight_historical_evidence_schema)
        await connection.run_sync(ensure_alembic_version_column_capacity)
        await connection.commit()
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
