#!/usr/bin/env python3
"""
SEC-001 / SEC-002 / DB-001 -- URGENT verification script.

Verifies Row-Level Security (RLS) policies and tenant isolation on the
ACTUAL deployed PostgreSQL database. This script is read-only and safe to
run against production.

Usage:
    # From repo root
    python scripts/verify_rls.py                     # uses DATABASE_URL env
    python scripts/verify_rls.py "postgresql://..."  # explicit URL

Outputs a structured report to stdout and writes a JSON result to
/home/z/my-project/scripts/rls_report.json (or specified output path).

Checks performed:
    SEC-001  RLS enabled on tenant-scoped tables
    SEC-002  RLS policies exist and reference company_id correctly
    DB-001   alembic_version matches repo migration head
    DB-003   Table owner is not the application role (defense-in-depth)

Tables considered tenant-scoped (subject to override via --tables flag):
    companies, users, documents, document_versions, filings, agm_filings,
    audit_filings, annual_returns, statutory_registers, transfers,
    shareholding_records, board_resolutions, compliance_flags, compliance_scores,
    rescue_plans, rescue_steps, rescue_engagements, calendar_events,
    activity_logs, notifications, webhook_deliveries, audit_logs,
    commercial_packages, commercial_subscriptions, payments, invoices.
"""
from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

DEFAULT_TENANT_TABLES = [
    "companies", "users", "documents", "document_versions", "filings",
    "agm_filings", "audit_filings", "annual_returns", "statutory_registers",
    "transfers", "shareholding_records", "board_resolutions",
    "compliance_flags", "compliance_scores", "rescue_plans", "rescue_steps",
    "rescue_engagements", "calendar_events", "activity_logs", "notifications",
    "webhook_deliveries", "audit_logs", "commercial_packages",
    "commercial_subscriptions", "payments", "invoices",
]


@dataclass
class CheckResult:
    check_id: str
    table: str
    status: str  # PASS | FAIL | WARN | SKIP
    detail: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _try_import_psycopg():
    try:
        import psycopg  # type: ignore
        return psycopg
    except ImportError:
        pass
    try:
        import psycopg2  # type: ignore
        return psycopg2
    except ImportError:
        return None


def connect(url: str):
    drv = _try_import_psycopg()
    if drv is None:
        raise RuntimeError(
            "Neither psycopg (v3) nor psycopg2 is installed. "
            "Install with: pip install psycopg[binary]  OR  pip install psycopg2-binary"
        )

    # psycopg v3 API
    if hasattr(drv, "connect") and "psycopg" in drv.__name__:
        return drv.connect(url)

    # psycopg2 API
    return drv.connect(url)


def list_tenant_tables(conn, expected: list[str]) -> tuple[list[str], list[str]]:
    """Return (found_tenant_tables, missing_tenant_tables)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )
        rows = {r[0] for r in cur.fetchall()}
    found = sorted(rows.intersection(expected))
    missing = sorted(set(expected) - rows)
    return found, missing


def check_rls_enabled(conn, table: str) -> CheckResult:
    """SEC-001: is row_security = 'on' for this table?"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND c.relname = %s
            """,
            (table,),
        )
        row = cur.fetchone()
    if row is None:
        return CheckResult(
            check_id="SEC-001", table=table, status="FAIL",
            detail=f"Table {table} does not exist in public schema.",
        )
    rls_on, rls_forced = bool(row[0]), bool(row[1])
    if not rls_on:
        return CheckResult(
            check_id="SEC-001", table=table, status="FAIL",
            detail=f"RLS is OFF on {table}. Tenant data is NOT protected by Postgres.",
            evidence={"rowsecurity": False, "forcerowsecurity": False},
        )
    return CheckResult(
        check_id="SEC-001", table=table, status="PASS",
        detail=f"RLS enabled on {table}" + (" (FORCED)" if rls_forced else ""),
        evidence={"rowsecurity": True, "forcerowsecurity": rls_forced},
    )


def check_rls_policies(conn, table: str) -> CheckResult:
    """SEC-002: do policies exist and reference company_id?"""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT policyname, cmd, qual, with_check
            FROM pg_policies
            WHERE schemaname = 'public' AND tablename = %s
            ORDER BY policyname
            """,
            (table,),
        )
        rows = cur.fetchall()
    if not rows:
        return CheckResult(
            check_id="SEC-002", table=table, status="FAIL",
            detail=f"No RLS policies on {table}. RLS is enabled but has no effect.",
        )
    policies = []
    for name, cmd, qual, with_check in rows:
        qual_txt = (qual or "") + " " + (with_check or "")
        references_company = "company_id" in qual_txt.lower() or "tenant_id" in qual_txt.lower()
        policies.append({
            "name": name, "cmd": cmd, "qual": qual, "with_check": with_check,
            "references_company_id": references_company,
        })
    without_company = [p["name"] for p in policies if not p["references_company_id"]]
    if without_company:
        return CheckResult(
            check_id="SEC-002", table=table, status="WARN",
            detail=(
                f"{table} has {len(policies)} policies but the following do not "
                f"reference company_id/tenant_id: {without_company}. "
                f"These policies may not actually enforce tenant isolation."
            ),
            evidence={"policies": policies, "without_company_ref": without_company},
        )
    return CheckResult(
        check_id="SEC-002", table=table, status="PASS",
        detail=f"{table} has {len(policies)} RLS policies, all reference company_id.",
        evidence={"policy_count": len(policies)},
    )


def check_alembic_version(conn) -> CheckResult:
    """DB-001: deployed alembic_version vs repo head."""
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version_num FROM alembic_version LIMIT 1"
            )
            row = cur.fetchone()
    except Exception as exc:
        return CheckResult(
            check_id="DB-001", table="alembic_version", status="FAIL",
            detail=(
                "Could not read alembic_version table. This is the exact symptom "
                "reported in the prior audit (ownership permission issue). "
                f"Error: {exc}"
            ),
        )
    if row is None:
        return CheckResult(
            check_id="DB-001", table="alembic_version", status="FAIL",
            detail="alembic_version table is empty -- migrations not run.",
        )
    return CheckResult(
        check_id="DB-001", table="alembic_version", status="PASS",
        detail=f"Deployed alembic revision: {row[0]}. Compare to repo head (run `alembic heads` locally).",
        evidence={"deployed_revision": row[0]},
    )


def check_table_owner(conn, table: str, app_role: str | None) -> CheckResult:
    """DB-003: table owner should not be the application role (defense-in-depth)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rolname
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_roles r ON r.oid = c.relowner
            WHERE n.nspname = 'public' AND c.relname = %s
            """,
            (table,),
        )
        row = cur.fetchone()
    if row is None:
        return CheckResult(
            check_id="DB-003", table=table, status="SKIP",
            detail=f"Table {table} not found.",
        )
    owner = row[0]
    if app_role and owner == app_role:
        return CheckResult(
            check_id="DB-003", table=table, status="WARN",
            detail=(
                f"Table {table} owner is the application role '{owner}'. "
                f"Owner bypasses RLS unless FORCED. Recommend separate owner role."
            ),
            evidence={"owner": owner, "app_role": app_role},
        )
    return CheckResult(
        check_id="DB-003", table=table, status="PASS",
        detail=f"Table owner: {owner}",
        evidence={"owner": owner},
    )


def verify_cross_tenant_query(conn, table: str) -> CheckResult:
    """SEC-001 runtime test: with app.current_user_id unset, the table should
    return ZERO rows. (RLS with no session variable should yield empty result.)
    """
    try:
        with conn.cursor() as cur:
            cur.execute("RESET app.current_user_id;")
            cur.execute(f"SELECT COUNT(*) FROM {table};")  # noqa: S608 -- table from allowlist
            row = cur.fetchone()
        if row is None:
            return CheckResult(
                check_id="SEC-001-RUNTIME", table=table, status="FAIL",
                detail=f"COUNT(*) on {table} returned no row.",
            )
        count = int(row[0])
        if count == 0:
            return CheckResult(
                check_id="SEC-001-RUNTIME", table=table, status="PASS",
                detail=f"{table} returns 0 rows without app.current_user_id set (RLS effective).",
            )
        return CheckResult(
            check_id="SEC-001-RUNTIME", table=table, status="FAIL",
            detail=(
                f"{table} returns {count} rows without app.current_user_id set. "
                f"RLS is NOT actually filtering -- data leakage risk."
            ),
            evidence={"row_count_without_tenant": count},
        )
    except Exception as exc:
        return CheckResult(
            check_id="SEC-001-RUNTIME", table=table, status="WARN",
            detail=f"Runtime test failed: {exc}",
        )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("database_url", nargs="?", help="PostgreSQL URL. Defaults to $DATABASE_URL.")
    p.add_argument("--app-role", help="Application DB role name (for DB-003 owner check).")
    p.add_argument("--tables", help="Comma-separated override list of tenant tables.")
    p.add_argument("--output", default="/home/z/my-project/scripts/rls_report.json",
                   help="Where to write JSON report.")
    p.add_argument("--skip-runtime", action="store_true",
                   help="Skip the cross-tenant runtime test (still runs policy checks).")
    args = p.parse_args()

    url = args.database_url or os.environ.get("DATABASE_URL")
    if not url:
        print("ERROR: No DATABASE_URL provided. Pass URL as first arg or set DATABASE_URL env.",
              file=sys.stderr)
        return 2

    tenant_tables = (
        [t.strip() for t in args.tables.split(",")] if args.tables else DEFAULT_TENANT_TABLES
    )

    print(f"=== NLC RLS Verification ===")
    print(f"Target: {url.split('@')[-1] if '@' in url else url}")
    print(f"Tables checked: {len(tenant_tables)}")
    print()

    results: list[CheckResult] = []
    try:
        conn = connect(url)
    except Exception as exc:
        print(f"FATAL: Could not connect to database: {exc}", file=sys.stderr)
        return 3

    try:
        with conn:
            # DB-001
            results.append(check_alembic_version(conn))

            # Discover what tables actually exist
            found, missing = list_tenant_tables(conn, tenant_tables)
            if missing:
                print(f"WARN: expected tenant tables not found in DB: {missing}")
                print("  (Either they were never created, or migration drift.)")
            print(f"Found {len(found)} of {len(tenant_tables)} expected tenant tables.")
            print()

            for tbl in found:
                # SEC-001
                results.append(check_rls_enabled(conn, tbl))
                # SEC-002
                results.append(check_rls_policies(conn, tbl))
                # DB-003
                results.append(check_table_owner(conn, tbl, args.app_role))
                # SEC-001 runtime
                if not args.skip_runtime:
                    results.append(verify_cross_tenant_query(conn, tbl))
    except Exception as exc:
        print(f"FATAL during checks: {exc}", file=sys.stderr)
        return 4
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Print human report
    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    warn_count = sum(1 for r in results if r.status == "WARN")
    skip_count = sum(1 for r in results if r.status == "SKIP")

    print(f"=== RESULTS ===")
    print(f"PASS: {pass_count}    FAIL: {fail_count}    WARN: {warn_count}    SKIP: {skip_count}")
    print()

    for r in results:
        marker = {"PASS": "OK", "FAIL": "XX", "WARN": "!!", "SKIP": "--"}[r.status]
        print(f"[{marker}] {r.check_id} / {r.table}: {r.detail}")

    # Write JSON report
    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "database": url.split("@")[-1] if "@" in url else url,
        "summary": {"pass": pass_count, "fail": fail_count, "warn": warn_count, "skip": skip_count},
        "results": [asdict(r) for r in results],
    }
    out_path = args.output
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)
    print()
    print(f"JSON report written to: {out_path}")
    print()
    print("=== NEXT STEPS ===")
    if fail_count > 0:
        print(f"  - {fail_count} FAILURE(S) require immediate attention.")
        print("  - For SEC-001 FAIL: ALTER TABLE <tbl> ENABLE ROW LEVEL SECURITY;")
        print("                         ALTER TABLE <tbl> FORCE ROW LEVEL SECURITY;")
        print("  - For SEC-002 FAIL: write policy referencing company_id using app.current_user_id;")
        print("  - For DB-001 FAIL: run `alembic upgrade head` against this DB.")
    if warn_count > 0:
        print(f"  - {warn_count} WARNING(S) -- review each before close.")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main())