#!/usr/bin/env python3
"""Validate and optionally ingest canonical finding-evidence manifests.

The ingester is fail-closed. It never backfills empty historical tables, does
not infer evidence, and does not create user/asserted evidence from guesses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import Json, execute_values


REQUIRED_FIELDS = {
    "binding_id",
    "company_id",
    "company_fact_id",
    "evidence_role",
    "fact_key",
    "fact_value_snapshot",
    "fact_value_canonical",
    "evidence_canonical",
    "fact_value_hash",
    "evidence_hash",
    "trust_level",
    "verification_status",
    "observed_on",
    "asserted_by",
}


def _stable_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_manifest(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("evidence")
    if not isinstance(payload, list):
        raise ValueError("Evidence manifest must be a JSON array or an object with evidence[]")
    return payload


def validate_manifest(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    validated = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"Evidence row {index} is not an object")
        missing = sorted(REQUIRED_FIELDS - set(row))
        if missing:
            raise ValueError(f"Evidence row {index} missing fields: {missing}")
        if row["trust_level"] not in {"USER_ASSERTED", "AUTHORIZED_DOCUMENT_BACKED"}:
            raise ValueError(f"Evidence row {index} has invalid trust_level")
        if row["verification_status"] not in {"UNVERIFIED", "VERIFIED", "REJECTED", "SUPERSEDED"}:
            raise ValueError(f"Evidence row {index} has invalid verification_status")
        if row["trust_level"] == "AUTHORIZED_DOCUMENT_BACKED":
            for field in ("document_id", "authorized_uploader_id", "uploaded_at", "source_reference"):
                if not row.get(field):
                    raise ValueError(
                        f"Evidence row {index} requires {field} for authorized document evidence"
                    )
        if row["verification_status"] == "VERIFIED" and row["trust_level"] != "AUTHORIZED_DOCUMENT_BACKED":
            raise ValueError(f"Evidence row {index} cannot be VERIFIED without document backing")
        if not isinstance(row["fact_value_snapshot"], (dict, list, str, int, float, bool, type(None))):
            raise ValueError(f"Evidence row {index} has invalid fact_value_snapshot")
        fact_value_hash = _stable_hash({"value": row["fact_value_snapshot"]})
        if row["fact_value_hash"] != fact_value_hash:
            raise ValueError(f"Evidence row {index} fact_value_hash mismatch")
        if hashlib.sha256(str(row["evidence_canonical"]).encode("utf-8")).hexdigest() != row["evidence_hash"]:
            raise ValueError(f"Evidence row {index} evidence_hash mismatch")
        validated.append(row)
    return validated


def apply_manifest(database_url: str, rows: list[dict[str, Any]]) -> int:
    columns = [
        "binding_id", "company_id", "company_fact_id", "evidence_role", "fact_key",
        "fact_value_snapshot", "fact_value_canonical", "evidence_canonical",
        "fact_value_hash", "trust_level", "verification_status", "observed_on",
        "source_reference", "document_id", "document_sha256", "asserted_by",
        "authorized_uploader_id", "uploaded_at", "verified_by", "verified_at",
        "evidence_hash",
    ]
    values = []
    for row in rows:
        values.append(tuple(
            Json(row["fact_value_snapshot"]) if column == "fact_value_snapshot"
            else row.get(column)
            for column in columns
        ))
    with psycopg2.connect(database_url.replace("postgresql+asyncpg://", "postgresql://")) as conn:
        with conn.cursor() as cur:
            execute_values(
                cur,
                """
                INSERT INTO public.compliance_finding_evidence (
                    binding_id, company_id, company_fact_id, evidence_role, fact_key,
                    fact_value_snapshot, fact_value_canonical, evidence_canonical,
                    fact_value_hash, trust_level, verification_status, observed_on,
                    source_reference, document_id, document_sha256, asserted_by,
                    authorized_uploader_id, uploaded_at, verified_by, verified_at,
                    evidence_hash
                ) VALUES %s
                ON CONFLICT (binding_id, company_fact_id) DO NOTHING
                """,
                values,
            )
            return cur.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path, help="JSON evidence manifest")
    parser.add_argument("--apply", action="store_true", help="Insert validated rows")
    parser.add_argument("--database-url")
    args = parser.parse_args()

    try:
        rows = validate_manifest(load_manifest(args.manifest))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"EVIDENCE INGESTION REJECTED: {exc}", file=sys.stderr)
        return 2

    print(f"EVIDENCE INGESTION VALIDATED: {len(rows)} row(s)")
    if not args.apply:
        print("DRY-RUN: no database rows changed")
        return 0

    database_url = args.database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL or --database-url is required with --apply", file=sys.stderr)
        return 2
    try:
        inserted = apply_manifest(database_url, rows)
    except Exception as exc:
        print(f"EVIDENCE INGESTION FAILED: {exc}", file=sys.stderr)
        return 1
    print(f"EVIDENCE INGESTION APPLIED: {inserted} row(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
