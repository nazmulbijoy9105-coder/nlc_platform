#!/usr/bin/env python3
"""Verify a PostgreSQL custom-format backup archive without connecting to a database.

This checks the archive TOC and the presence of both table-definition and
table-data entries for the three historical evidence tables. It does NOT prove
that rows are present or that a restore will succeed. An isolated restore
rehearsal is mandatory.
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


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        actual = file_sha256(args.archive)
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
        definition = rf"\bTABLE\s+public\s+{re.escape(table)}\b"
        data = rf"\bTABLE DATA\s+public\s+{re.escape(table)}\b"
        has_definition = re.search(definition, toc) is not None
        has_data = re.search(data, toc) is not None
        if has_definition and has_data:
            print(f"PASS: archive contains table definition and data entries for public.{table}")
        else:
            if not has_definition:
                print(f"FAIL: archive has no table definition entry public.{table}")
            if not has_data:
                print(f"FAIL: archive has no table data entry public.{table}")
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
