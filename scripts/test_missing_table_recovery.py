"""CI-only destructive rehearsal for migration 0044's missing-table recovery.

This script must run only against the disposable nlc_test_baseline_0042 database.
It intentionally drops three reconstructed schema objects, upgrades to head,
and verifies that 0044 recreates the schema without inventing historical rows.
"""
from __future__ import annotations

import asyncio
import os
import subprocess

import asyncpg


async def main() -> None:
    raw_url = os.environ.get("DATABASE_URL", "")
    if not raw_url.startswith("postgresql+asyncpg://"):
        raise SystemExit("Refusing: DATABASE_URL is not the expected CI asyncpg URL")
    database_name = raw_url.rsplit("/", 1)[-1].split("?", 1)[0]
    if database_name != "nlc_test_baseline_0042":
        raise SystemExit(
            "Refusing destructive recovery test outside nlc_test_baseline_0042"
        )

    url = raw_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(url)
    try:
        identity = await conn.fetchrow("""
            SELECT current_database() AS database_name,
                   (SELECT version_num FROM alembic_version LIMIT 1) AS revision
        """)
        if identity["database_name"] != "nlc_test_baseline_0042":
            raise SystemExit("Refusing: connected database name is not the CI fixture")
        if identity["revision"] != "0042_dedup_key":
            raise SystemExit(
                "Refusing: expected fixture revision 0042_dedup_key, "
                f"found {identity['revision']!r}"
            )

        existing = await conn.fetch("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_name = ANY($1::text[])
        """, ["webhook_endpoints", "webhook_deliveries", "rescue_audit_log"])
        if {row["table_name"] for row in existing} != {
            "webhook_endpoints", "webhook_deliveries", "rescue_audit_log"
        }:
            raise AssertionError(
                "The 0042 fixture does not contain all three original tables"
            )

        # Drop only the three disposable fixture tables, without CASCADE.
        await conn.execute("""
            DROP TABLE public.webhook_deliveries,
                       public.webhook_endpoints,
                       public.rescue_audit_log
        """)
    finally:
        await conn.close()

    subprocess.run(["alembic", "upgrade", "head"], check=True, env=os.environ.copy())

    conn = await asyncpg.connect(url)
    try:
        rows = await conn.fetch("""
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity,
                   obj_description(c.oid, 'pg_class') AS table_comment
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relname = ANY($1::text[])
            ORDER BY c.relname
        """, ["webhook_endpoints", "webhook_deliveries", "rescue_audit_log"])
        if len(rows) != 3:
            raise AssertionError(f"Expected all 3 recovery tables, found {len(rows)}")
        for row in rows:
            if not row["relrowsecurity"] or not row["relforcerowsecurity"]:
                raise AssertionError(f"{row['relname']} is not ENABLE + FORCE RLS")
            if "SCHEMA-ONLY RECONSTRUCTION" not in (row["table_comment"] or ""):
                raise AssertionError(
                    f"{row['relname']} is missing the schema-only recovery disclosure"
                )

        for table in ("webhook_endpoints", "webhook_deliveries", "rescue_audit_log"):
            count = await conn.fetchval(f'SELECT count(*) FROM public."{table}"')
            if count != 0:
                raise AssertionError(
                    f"{table} unexpectedly contains rows after schema-only reconstruction"
                )

        fk = await conn.fetchrow("""
            SELECT conname, confdeltype
            FROM pg_constraint
            WHERE conrelid = 'public.rescue_audit_log'::regclass
              AND confrelid = 'public.rescue_plans'::regclass
              AND contype = 'f'
        """)
        if not fk or fk["confdeltype"] != "r":
            raise AssertionError(
                "rescue_audit_log -> rescue_plans must use ON DELETE RESTRICT"
            )

        expected_indexes = {
            "idx_webhook_endpoints_user",
            "idx_webhook_endpoints_active",
            "idx_webhook_deliveries_endpoint",
            "idx_webhook_deliveries_pending",
            "idx_webhook_deliveries_retry",
            "ix_rescue_audit_log_plan_id",
            "ix_rescue_audit_log_actor_id",
            "ix_rescue_audit_log_finding_id",
            "ix_rescue_audit_log_created_at",
        }
        actual_indexes = await conn.fetch("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = ANY($1::text[])
        """, ["webhook_endpoints", "webhook_deliveries", "rescue_audit_log"])
        actual = {row["indexname"] for row in actual_indexes}
        missing = sorted(expected_indexes - actual)
        if missing:
            raise AssertionError(f"Missing recovery indexes: {missing}")
    finally:
        await conn.close()

    print(
        "PASS: 0044 reconstructed all 3 missing schemas, preserved empty-history "
        "disclosure, enabled+forced RLS, restored indexes and RESTRICT FK."
    )


if __name__ == "__main__":
    asyncio.run(main())
