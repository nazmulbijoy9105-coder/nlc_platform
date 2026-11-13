"""CI-only destructive test for the fail-closed 0042 restore-schema guard.

This script must run only against the separate disposable
nlc_test_missing_table_guard database. It drops the three tables created by
0037/0038, attempts a normal Alembic upgrade, and proves that env.py refuses
before any migration DDL or schema-only reconstruction occurs.
"""
from __future__ import annotations

import asyncio
import os
import subprocess

import asyncpg


EXPECTED_DATABASE = "nlc_test_missing_table_guard"
REQUIRED_TABLES = (
    "webhook_endpoints",
    "webhook_deliveries",
    "rescue_audit_log",
)
GUARD_MESSAGE = "Refusing Alembic execution before 0044_webhook_schema_reconcile"


async def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url.startswith("postgresql+asyncpg://"):
        raise SystemExit("Refusing: DATABASE_URL is not the expected CI asyncpg URL")
    database_name = raw_url.rsplit("/", 1)[-1].split("?", 1)[0]
    if database_name != EXPECTED_DATABASE:
        raise SystemExit(
            f"Refusing destructive guard test outside {EXPECTED_DATABASE}"
        )

    url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        identity = await conn.fetchrow(
            """
            SELECT current_database() AS database_name,
                   (SELECT version_num FROM public.alembic_version LIMIT 1) AS revision
            """
        )
        if identity["database_name"] != EXPECTED_DATABASE:
            raise SystemExit("Refusing: connected database is not the CI fixture")
        if identity["revision"] != "0042_dedup_key":
            raise SystemExit(
                "Refusing: expected fixture revision 0042_dedup_key, "
                f"found {identity['revision']!r}"
            )

        existing = await conn.fetch(
            """
            SELECT table_name
              FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_name = ANY($1::text[])
            """,
            list(REQUIRED_TABLES),
        )
        if {row["table_name"] for row in existing} != set(REQUIRED_TABLES):
            raise AssertionError(
                "The fresh 0042 fixture must contain all three 0037/0038 tables "
                "before the test removes them."
            )

        # This destructive operation is confined to the named disposable CI DB.
        await conn.execute(
            """
            DROP TABLE public.webhook_deliveries,
                       public.webhook_endpoints,
                       public.rescue_audit_log
            """
        )
    finally:
        await conn.close()

    env = os.environ.copy()
    env["DATABASE_URL"] = raw_url
    env["ENVIRONMENT"] = "test"
    env.pop("MIGRATION_DATABASE_URL", None)
    result = subprocess.run(
        ["alembic", "upgrade", "head"],
        check=False,
        env=env,
        capture_output=True,
        text=True,
    )
    output = (result.stdout or "") + "\\n" + (result.stderr or "")
    if result.returncode == 0:
        raise AssertionError(
            "Alembic unexpectedly advanced despite missing pre-0042 evidence tables."
        )
    if GUARD_MESSAGE not in output:
        raise AssertionError(
            "Alembic failed for an unexpected reason instead of the schema guard:\\n"
            + output[-8000:]
        )

    conn = await asyncpg.connect(url)
    try:
        revision = await conn.fetchval(
            "SELECT version_num FROM public.alembic_version LIMIT 1"
        )
        if revision != "0042_dedup_key":
            raise AssertionError(
                f"Schema guard changed Alembic revision unexpectedly: {revision!r}"
            )
        remaining = await conn.fetch(
            """
            SELECT table_name
              FROM information_schema.tables
             WHERE table_schema = 'public'
               AND table_name = ANY($1::text[])
            """,
            list(REQUIRED_TABLES),
        )
        if remaining:
            raise AssertionError(
                "Schema guard unexpectedly recreated tables: "
                f"{[row['table_name'] for row in remaining]!r}"
            )
    finally:
        await conn.close()

    print(
        "PASS: missing 0037/0038 tables block Alembic before 0044; "
        "revision remains 0042 and no schema-only tables are recreated."
    )


if __name__ == "__main__":
    asyncio.run(main())
