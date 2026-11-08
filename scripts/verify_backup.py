#!/usr/bin/env python3
"""Verify a PostgreSQL custom-format backup archive without connecting to a database.

This checks the archive TOC and the presence of the three historical evidence
table definitions. It does NOT prove that rows are present or that a restore
will succeed. A separate isolated restore rehearsal is mandatory.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
from pathlib import Path

REQUIRED_EVIDENCE_TABLES = (
    "webhook_endpoints",
    "webhook_deliveries",
    "rescue_audit_log",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path, help="pg_dump custom-format archive")
    args = parser.parse_args()

    pg_restore = shutil.which("pg_restore")
    if not pg_restore:
        print("FAIL: pg_restore is not installed", file=sys.stderr)
        return 2
    if not args.archive.is_file() or args.archive.stat().st_size == 0:
        print(f"FAIL: archive is missing or empty: {args.archive}", file=sys.stderr)
        return 2

    checksum_path = Path(f"{args.archive}.sha256")
    if checksum_path.exists():
        expected = checksum_path.read_text(encoding="utf-8").split()[0]
        actual = hashlib.sha256(args.archive.read_bytes()).hexdigest()
        if actual.lower() != expected.lower():
            print("FAIL: SHA-256 checksum mismatch", file=sys.stderr)
            return 1
        print(f"PASS: SHA-256 {actual}")
    else:
        print("WARN: no adjacent .sha256 file; checksum was not checked")

    result = subprocess.run(
        [pg_restore, "--list", str(args.archive)],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("FAIL: pg_restore could not read the archive TOC", file=sys.stderr)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
        return 1

    toc = result.stdout
    print(f"PASS: PostgreSQL archive TOC readable ({args.archive.stat().st_size} bytes)")
    missing = []
    for table in REQUIRED_EVIDENCE_TABLES:
        pattern = rf"\bTABLE\s+public\s+{re.escape(table)}\b"
        if re.search(pattern, toc):
            print(f"PASS: archive contains table definition entry public.{table}")
        else:
            print(f"FAIL: archive has no table definition entry public.{table}")
            missing.append(table)

    if missing:
        print("Archive is NOT a recovery candidate for all required evidence tables.")
        return 1

    print(
        "ARCHIVE CHECK PASSED. No database connection or restore was performed; "
        "row counts and restoreability remain unverified."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
