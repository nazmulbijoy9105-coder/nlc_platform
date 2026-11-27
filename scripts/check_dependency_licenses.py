"""Fail closed when any installed dependency license lacks explicit approval."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


# Owner-approved permissive licenses only. PSFL/PSF, GPL/AGPL, LGPL, MPL,
# SSPL, BUSL, unknown and unclassified licenses remain blocked pending review.
APPROVED_ALIASES = {
    "MIT",
    "MIT LICENSE",
    "BSD LICENSE",
    "BSD 2 CLAUSE LICENSE",
    "BSD 2 CLAUSE SIMPLIFIED LICENSE",
    "BSD 3 CLAUSE LICENSE",
    "BSD 3 CLAUSE CLEAR LICENSE",
    "BSD 3 CLAUSE REVISED LICENSE",
    "BSD 3 CLAUSE NEW OR REVISED LICENSE",
    "BSD 2 CLAUSE",
    "BSD 3 CLAUSE",
    "APACHE SOFTWARE LICENSE",
    "APACHE LICENSE 2 0",
    "APACHE 2 0",
    "ISC LICENSE",
    "ISC",
}


def normalize(value: object) -> str:
    return re.sub(r"[^A-Z0-9]+", " ", str(value or "").upper()).strip()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: check_dependency_licenses.py INVENTORY.json")
    rows = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    if not isinstance(rows, list) or not rows:
        raise SystemExit("Dependency license inventory is empty or malformed")

    offenders = []
    for row in rows:
        name = str(row.get("Name") or "<unnamed>")
        license_name = str(row.get("License") or "").strip()
        if normalize(license_name) not in APPROVED_ALIASES:
            offenders.append(f"{name}: {license_name or 'UNKNOWN / UNDECLARED'}")

    if offenders:
        raise SystemExit(
            "Unapproved or unknown dependency licenses (fail-closed):\n"
            + "\n".join(sorted(offenders))
        )
    print(f"License policy passed for {len(rows)} installed application dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
