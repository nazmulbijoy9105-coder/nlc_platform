#!/usr/bin/env python3
"""Audit ownership and RLS state for every public base table."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor


def audit_governance(conn) -> dict[str, Any]:
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute(
        """
        SELECT c.relname AS table_name,
               r.rolname AS owner,
               c.relrowsecurity AS rls_enabled,
               c.relforcerowsecurity AS rls_forced
          FROM pg_class c
          JOIN pg_namespace n ON n.oid = c.relnamespace
          JOIN pg_roles r ON r.oid = c.relowner
         WHERE n.nspname = 'public'
           AND c.relkind IN ('r', 'p')
         ORDER BY c.relname
        """
    )
    tables = cur.fetchall()

    cur.execute(
        """
        SELECT schemaname, tablename, policyname, permissive, roles, cmd,
               qual, with_check
          FROM pg_policies
         WHERE schemaname = 'public'
         ORDER BY tablename, policyname
        """
    )
    policies = cur.fetchall()
    policy_by_table: dict[str, list[dict[str, Any]]] = {}
    for policy in policies:
        policy_by_table.setdefault(policy["tablename"], []).append(dict(policy))

    inventory = []
    failures = []
    for table in tables:
        item = dict(table)
        item["policies"] = policy_by_table.get(item["table_name"], [])
        inventory.append(item)
        if item["owner"] not in {"nlc_migration_owner", "neondb_owner"}:
            failures.append(
                f"{item['table_name']}: unexpected owner {item['owner']}"
            )

    migration_tables = {
        item["table_name"] for item in inventory
        if item["owner"] == "nlc_migration_owner"
    }
    return {
        "audit": "public-table-ownership-and-rls",
        "table_count": len(inventory),
        "migration_owner_table_count": len(migration_tables),
        "tables": inventory,
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-output", type=Path)
    parser.add_argument("--database-url")
    args = parser.parse_args()

    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL or --database-url is required", file=sys.stderr)
        return 2
    database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")

    with psycopg2.connect(database_url) as conn:
        conn.set_session(readonly=True, autocommit=True)
        report = audit_governance(conn)

    rendered = json.dumps(report, indent=2, default=str)
    print(rendered)
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(rendered + "\n", encoding="utf-8")

    if report["failures"]:
        print("PUBLIC TABLE GOVERNANCE FAILED", file=sys.stderr)
        for failure in report["failures"]:
            print(f"  - {failure}", file=sys.stderr)
        return 1
    print(
        f"PUBLIC TABLE GOVERNANCE PASSED: {report['table_count']} public base tables inventoried"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
