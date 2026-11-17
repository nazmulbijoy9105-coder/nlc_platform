"""Read-only inventory of historical references to colliding rule IDs.

This tool finds candidate references; it does NOT prove historical attribution.
Every hit remains UNATTRIBUTED until the exact rule definition, evaluator build,
evaluation inputs and evidence can be bound to that record.
"""
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

import sqlalchemy as sa


TARGET_RULE_IDS = ("INC-001", "INC-002")
SCHEMA = "public"
# Catalogue rows and their quarantine archive are sources, not finding references.
EXCLUDED_REFERENCE_TABLES = {"legal_rules", "legal_rule_identity_archive"}


def classify_reference_match(
    rule_id: str, table: str, column: str, locator: dict[str, Any]
) -> dict[str, Any]:
    """A text/JSON match proves reference presence only, never rule attribution."""
    return {
        "rule_id": rule_id,
        "table": table,
        "column": column,
        "record_locator": locator,
        "attribution_status": "UNATTRIBUTED",
        "reason": (
            "Reference presence does not bind the historical definition, "
            "evaluator version, evaluation inputs or evidence."
        ),
    }


def _is_candidate_type(column_type: Any) -> bool:
    return isinstance(
        column_type,
        (sa.String, sa.Text, sa.JSON, sa.ARRAY),
    ) or column_type.__class__.__name__.upper() == "JSONB"


def scan_connection(connection: sa.Connection) -> dict[str, Any]:
    inspector = sa.inspect(connection)
    matches: list[dict[str, Any]] = []
    scanned_columns = 0
    skipped_tables: list[str] = []
    excluded_tables: list[str] = []

    for table_name in inspector.get_table_names(schema=SCHEMA):
        if table_name in EXCLUDED_REFERENCE_TABLES:
            excluded_tables.append(table_name)
            continue
        columns = inspector.get_columns(table_name, schema=SCHEMA)
        candidate_columns = [
            column["name"] for column in columns
            if _is_candidate_type(column["type"])
        ]
        if not candidate_columns:
            continue

        primary_key = inspector.get_pk_constraint(
            table_name, schema=SCHEMA
        ).get("constrained_columns") or []
        table = sa.Table(
            table_name, sa.MetaData(), schema=SCHEMA, autoload_with=connection
        )
        if not primary_key:
            skipped_tables.append(table_name)

        for column_name in candidate_columns:
            scanned_columns += 1
            value = sa.cast(table.c[column_name], sa.Text)
            for rule_id in TARGET_RULE_IDS:
                statement = sa.select(
                    *[table.c[name] for name in primary_key]
                ).where(value.like(f"%{rule_id}%"))
                if not primary_key:
                    statement = sa.select(
                        sa.literal_column("ctid::text").label("ctid")
                    ).select_from(table).where(value.like(f"%{rule_id}%"))
                rows = connection.execute(statement).mappings()
                for row in rows:
                    locator = {
                        key: str(item) for key, item in row.items()
                    }
                    matches.append(
                        classify_reference_match(
                            rule_id, table_name, column_name, locator
                        )
                    )

    counts = Counter(item["rule_id"] for item in matches)
    return {
        "audit": "historical-rule-reference-inventory",
        "read_only": True,
        "schema": SCHEMA,
        "target_rule_ids": list(TARGET_RULE_IDS),
        "scanned_text_json_array_columns": scanned_columns,
        "candidate_reference_count": len(matches),
        "candidate_references_by_rule": {
            rule_id: counts.get(rule_id, 0) for rule_id in TARGET_RULE_IDS
        },
        "tables_without_primary_key": sorted(skipped_tables),
        "excluded_source_tables": sorted(excluded_tables),
        "attribution_status": "UNATTRIBUTED",
        "attribution_warning": (
            "This inventory does not prove attribution. Do not relabel or replay "
            "historical findings from rule_id matches alone."
        ),
        "references": matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only scan for INC-001/INC-002 historical references."
    )
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()

    database_url = os.environ.get("NLC_HISTORICAL_AUDIT_DATABASE_URL")
    if not database_url:
        raise SystemExit(
            "Set NLC_HISTORICAL_AUDIT_DATABASE_URL to a read-only audit/restore "
            "database. DATABASE_URL is intentionally not used."
        )

    engine = sa.create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            with connection.begin():
                connection.exec_driver_sql("SET TRANSACTION READ ONLY")
                report = scan_connection(connection)
        rendered = json.dumps(report, indent=2, sort_keys=True, default=str)
        print(rendered)
        if args.json_output:
            args.json_output.write_text(rendered + "\n", encoding="utf-8")
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
