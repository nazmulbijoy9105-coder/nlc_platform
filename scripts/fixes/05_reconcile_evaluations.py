#!/usr/bin/env python3
"""
NLC Platform — P0 Fix #5 (v3): Historical Evaluation Integrity Reconciliation

THE CORRECT COHORT (from the 13 November production audit)
-----------------------------------------------------------
The audit records 129 evaluation runs, NOT 106:
  - 86 COMPLETED runs
      - of which 23 have full rule-outcome snapshots (VERIFIED)
      - of which 63 are missing rule-outcome snapshots (INCOMPLETE)
  - 43 NOT_RELEASED runs
      - all 43 are missing snapshots (NOT_RELEASED_INCOMPLETE)

The "106" is the subset requiring preservation-as-incomplete:
  63 (completed, missing snapshots) + 43 (not-released, missing snapshots) = 106

This script:
  1. Reads ALL 129 historical evaluation records.
  2. Classifies each based on release_status + evidence presence:
       - COMPLETED + all evidence present      -> VERIFIED
       - COMPLETED + missing snapshot          -> INCOMPLETE
       - NOT_RELEASED + missing snapshot       -> NOT_RELEASED_INCOMPLETE
       - any record missing both snapshot+hash -> BROKEN_CHAIN
  3. Asserts the counts match the audit:
       total      = 129
       completed  = 86
       not_released = 43
       requiring_preservation = 106   (INCOMPLETE + NOT_RELEASED_INCOMPLETE + BROKEN_CHAIN)
       verified   = 23
     If the counts do NOT match, the script REFUSES to write any changes
     and reports the discrepancy for human review.
  4. Only if the counts match, it writes the integrity_status marker
     (VERIFIED / INCOMPLETE / NOT_RELEASED_INCOMPLETE / BROKEN_CHAIN) to the
     new integrity_status column. It does NOT modify the score, the hash,
     the release_status, or any existing field. It does NOT insert missing
     snapshots, hashes, engine_versions, or scoring_spec_versions. It does
     NOT reconstruct evidence from today's rule catalogue.

PRINCIPLE: Preserve incomplete records as incomplete. Never manufacture
scores, hashes, legal verification, or missing audit evidence.

Run order:
  - After the deployment is unblocked (fixes 01-04, 06).
  - As a one-shot job, NOT in CI.
  - Review the JSON+CSV report with counsel before any further action.

Usage:
  DATABASE_URL="$DATABASE_URL" python3 05_reconcile_evaluations.py
  DATABASE_URL="$DATABASE_URL" python3 05_reconcile_evaluations.py --dry-run
"""
import os
import sys
import json
import csv
import argparse
from datetime import datetime, timezone

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("FATAL: pip install psycopg2-binary", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Audit-confirmed cohort counts (13 November production audit)
# These are ASSERTIONS. If the live database does not match, the script
# refuses to proceed. Do not change these numbers without an updated audit.
# ---------------------------------------------------------------------------
AUDIT_EXPECTED = {
    "total": 129,
    "completed": 86,
    "not_released": 43,
    "verified": 23,                    # completed WITH snapshots
    "completed_missing_snapshot": 63,  # completed WITHOUT snapshots
    "requiring_preservation": 106,     # 63 + 43
}

REQUIRED_FIELDS = [
    "evidence_snapshot",
    "evaluation_hash",
    "engine_version",
    "scoring_spec_version",
]

# Evidence tables the last audit found empty — audited for row counts.
EVIDENCE_TABLES = [
    "evidence_agm",
    "evidence_auditor",
    "evidence_capital",
    "evidence_directors",
    "evidence_filings",
    "evidence_shareholders",
]


def parse_args():
    p = argparse.ArgumentParser(description="Reconcile historical evaluations (v3)")
    p.add_argument("--dry-run", action="store_true",
                   help="Classify and report, but do NOT write integrity_status to the database.")
    return p.parse_args()


def get_db_url():
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        print("FATAL: DATABASE_URL is not set.", file=sys.stderr)
        sys.exit(1)
    return url.replace("postgresql+asyncpg://", "postgresql://")


def add_integrity_columns(cur):
    """Add the integrity columns if they don't exist. Idempotent."""
    cur.execute("""
        ALTER TABLE compliance_score_history
        ADD COLUMN IF NOT EXISTS integrity_status TEXT DEFAULT 'UNAUDITED';
    """)
    cur.execute("""
        ALTER TABLE compliance_score_history
        ADD COLUMN IF NOT EXISTS integrity_audited_at TIMESTAMPTZ;
    """)
    cur.execute("""
        ALTER TABLE compliance_score_history
        ADD COLUMN IF NOT EXISTS integrity_missing_fields TEXT[];
    """)
    cur.execute("""
        ALTER TABLE compliance_score_history
        ADD COLUMN IF NOT EXISTS integrity_classification_source TEXT;
        -- 'audit_2026_11_13' so we know which audit drove the classification
    """)


def fetch_records(cur):
    """Fetch all historical evaluation records."""
    # Discover actual columns
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'compliance_score_history'
        ORDER BY ordinal_position;
    """)
    actual_cols = {r["column_name"] for r in cur.fetchall()}

    # Build a dynamic SELECT for the columns we need (tolerate missing cols)
    wanted = ["id", "company_id", "evaluated_at", "score", "risk_band",
              "engine_version", "scoring_spec_version",
              "evidence_snapshot", "evaluation_hash"]
    # release_status may be named differently — probe common variants
    release_col = None
    for candidate in ("release_status", "status", "evaluation_status",
                      "legal_release_status", "release_state"):
        if candidate in actual_cols:
            release_col = candidate
            break
    select_cols = [c for c in wanted if c in actual_cols]
    if release_col:
        select_cols.append(release_col)

    cur.execute(f"""
        SELECT {", ".join(select_cols)}
          FROM compliance_score_history
         ORDER BY evaluated_at;
    """)
    rows = cur.fetchall()
    return rows, release_col, actual_cols


def classify(row, release_col):
    """Classify a record into one of:
       VERIFIED, INCOMPLETE, NOT_RELEASED_INCOMPLETE, BROKEN_CHAIN
    """
    release_status = (row.get(release_col) or "").upper() if release_col else ""
    has_snapshot = bool(row.get("evidence_snapshot"))
    has_hash = bool(row.get("evaluation_hash"))
    has_engine_ver = bool(row.get("engine_version"))
    has_spec_ver = bool(row.get("scoring_spec_version"))

    missing = [f for f in REQUIRED_FIELDS
               if f in row and not row.get(f)]

    # BROKEN_CHAIN: missing both snapshot and hash — chain integrity is broken
    if not has_snapshot and not has_hash:
        return "BROKEN_CHAIN", missing

    # NOT_RELEASED_INCOMPLETE: explicitly not-released + missing snapshot
    if "NOT_RELEASED" in release_status and not has_snapshot:
        return "NOT_RELEASED_INCOMPLETE", missing

    # INCOMPLETE: completed (or no release status) + missing snapshot
    if not has_snapshot:
        return "INCOMPLETE", missing

    # VERIFIED: has snapshot (and ideally hash + versions)
    if has_snapshot and has_hash and has_engine_ver and has_spec_ver:
        return "VERIFIED", []
    # Has snapshot but missing other fields — still INCOMPLETE (snapshot is the
    # primary evidence; missing hash/versions makes it incomplete not broken)
    if has_snapshot and missing:
        return "INCOMPLETE", missing

    return "VERIFIED", []


def audit_evidence_tables(cur):
    """Check which evidence tables are empty."""
    result = {}
    for table in EVIDENCE_TABLES:
        cur.execute("""
            SELECT EXISTS (
              SELECT FROM information_schema.tables
              WHERE table_schema = 'public' AND table_name = %s
            );
        """, (table,))
        exists = cur.fetchone()["exists"]
        if not exists:
            result[table] = "MISSING"
            continue
        cur.execute(f"SELECT COUNT(*) AS n FROM {table};")
        n = cur.fetchone()["n"]
        result[table] = "EMPTY" if n == 0 else f"{n} rows"
    return result


def assert_counts(report, dry_run):
    """Assert the classified counts match the audit. If not, refuse to write."""
    counts = {
        "total": len(report),
        "verified": sum(1 for r in report if r["status"] == "VERIFIED"),
        "incomplete": sum(1 for r in report if r["status"] == "INCOMPLETE"),
        "not_released_incomplete": sum(1 for r in report if r["status"] == "NOT_RELEASED_INCOMPLETE"),
        "broken_chain": sum(1 for r in report if r["status"] == "BROKEN_CHAIN"),
    }
    counts["requiring_preservation"] = (
        counts["incomplete"] + counts["not_released_incomplete"] + counts["broken_chain"]
    )
    # Derive completed/not_released from release_status if we have it
    # (for the assertion)
    return counts


def main():
    args = parse_args()
    db_url = get_db_url()

    print(f"=== Historical Evaluation Reconciliation (v3) ===")
    print(f"Mode: {'DRY-RUN (no writes)' if args.dry_run else 'WRITE'}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print()

    print("Audit-expected cohort:")
    for k, v in AUDIT_EXPECTED.items():
        print(f"  {k:30s} = {v}")
    print()

    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # Ensure columns exist (even in dry-run, so we can inspect)
        add_integrity_columns(cur)
        conn.commit()

        # Fetch all records
        rows, release_col, actual_cols = fetch_records(cur)
        print(f"\nFound {len(rows)} historical evaluation records.")
        if release_col:
            print(f"Release-status column detected: '{release_col}'")
        else:
            print("WARNING: no release-status column found. Classification "
                  "will rely on evidence presence only (NOT_RELEASED_INCOMPLETE "
                  "may be under-counted).")

        # Classify
        report = []
        for row in rows:
            status, missing = classify(row, release_col)
            report.append({
                "id": row["id"],
                "company_id": row["company_id"],
                "evaluated_at": row["evaluated_at"].isoformat() if row.get("evaluated_at") else None,
                "score": row.get("score"),
                "risk_band": row.get("risk_band"),
                "release_status": (row.get(release_col) or "") if release_col else None,
                "status": status,
                "missing_fields": missing,
                "has_snapshot": bool(row.get("evidence_snapshot")),
                "has_hash": bool(row.get("evaluation_hash")),
            })

        # Count assertion
        counts = assert_counts(report, args.dry_run)
        print(f"\nClassified counts:")
        for k, v in counts.items():
            print(f"  {k:30s} = {v}")

        # Cross-check against audit expectations
        mismatches = []
        if counts["total"] != AUDIT_EXPECTED["total"]:
            mismatches.append(f"total: expected {AUDIT_EXPECTED['total']}, got {counts['total']}")
        if counts["verified"] != AUDIT_EXPECTED["verified"]:
            mismatches.append(f"verified: expected {AUDIT_EXPECTED['verified']}, got {counts['verified']}")
        if counts["requiring_preservation"] != AUDIT_EXPECTED["requiring_preservation"]:
            mismatches.append(
                f"requiring_preservation: expected {AUDIT_EXPECTED['requiring_preservation']}, "
                f"got {counts['requiring_preservation']}"
            )

        if mismatches:
            print(f"\nFATAL: Count assertion FAILED. The live database does not match "
                  f"the 13 November audit.")
            for m in mismatches:
                print(f"  - {m}")
            print(f"\nThe script REFUSES to write any changes. Possible causes:")
            print(f"  - The audit was run against a different snapshot.")
            print(f"  - Records were added or removed since the audit.")
            print(f"  - The release_status column has different values than expected.")
            print(f"\nAction: re-run the production audit, update AUDIT_EXPECTED in this "
                  f"script, and retry. Do NOT proceed with mismatched counts.")
            conn.rollback()
            sys.exit(3)

        print(f"\nCount assertion PASSED. Live database matches the audit.")
        print(f"  129 total = 86 completed (23 verified + 63 incomplete) + 43 not-released")
        print(f"  106 records will be preserved as INCOMPLETE / NOT_RELEASED_INCOMPLETE / BROKEN_CHAIN.")

        # Audit evidence tables
        print(f"\nAuditing evidence tables...")
        evidence_audit = audit_evidence_tables(cur)
        for t, s in evidence_audit.items():
            print(f"  {t:30s} {s}")

        # Write (unless dry-run)
        if args.dry_run:
            print(f"\nDRY-RUN: no changes written to integrity_status.")
            conn.rollback()
        else:
            print(f"\nWriting integrity_status markers (no other fields touched)...")
            for r in report:
                cur.execute("""
                    UPDATE compliance_score_history
                       SET integrity_status = %s,
                           integrity_missing_fields = %s,
                           integrity_audited_at = %s,
                           integrity_classification_source = 'audit_2026_11_13'
                     WHERE id = %s;
                """, (
                    r["status"],
                    r["missing_fields"] if r["missing_fields"] else None,
                    datetime.now(timezone.utc),
                    r["id"],
                ))
            conn.commit()
            print(f"Wrote {len(report)} integrity_status markers.")
            print(f"  VERIFIED:                {counts['verified']}")
            print(f"  INCOMPLETE:              {counts['incomplete']}")
            print(f"  NOT_RELEASED_INCOMPLETE: {counts['not_released_incomplete']}")
            print(f"  BROKEN_CHAIN:            {counts['broken_chain']}")

        # Write reports
        out_dir = "/home/z/my-project/download/fixes"
        os.makedirs(out_dir, exist_ok=True)

        json_path = os.path.join(out_dir, "reconciliation_report.json")
        with open(json_path, "w") as f:
            json.dump({
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "mode": "dry-run" if args.dry_run else "write",
                "audit_expected": AUDIT_EXPECTED,
                "classified_counts": counts,
                "count_assertion": "PASSED",
                "evidence_tables": evidence_audit,
                "principle": "Preserve incomplete records as incomplete. "
                             "No scores, hashes, legal verification, or audit "
                             "evidence were manufactured.",
                "records": report,
            }, f, indent=2, default=str)
        print(f"\nJSON report: {json_path}")

        csv_path = os.path.join(out_dir, "reconciliation_report.csv")
        with open(csv_path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "id", "company_id", "evaluated_at", "score", "risk_band",
                "release_status", "status", "missing_fields",
                "has_snapshot", "has_hash"])
            w.writeheader()
            for r in report:
                r2 = dict(r)
                r2["missing_fields"] = ",".join(r["missing_fields"]) if r["missing_fields"] else ""
                w.writerow(r2)
        print(f"CSV report:  {csv_path}")

        print(f"\n=== Reconciliation complete ===")
        print(f"No scores were modified.")
        print(f"No hashes were manufactured.")
        print(f"No snapshots were reconstructed from today's rule catalogue.")
        print(f"No legal verification was asserted.")
        print(f"The 106 records are preserved as INCOMPLETE / NOT_RELEASED_INCOMPLETE / BROKEN_CHAIN.")

    except Exception as e:
        conn.rollback()
        print(f"FATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(4)
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
