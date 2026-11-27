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


def _normalize_expression(value: object) -> str:
    """Normalize an SPDX-like expression while preserving grouping parentheses."""
    expression = str(value or "").upper()
    expression = re.sub(r"\b(AND|OR)\b", r" \1 ", expression)
    expression = re.sub(r"[^A-Z0-9()]+", " ", expression)
    return re.sub(r"\s+", " ", expression).strip()


def _split_top_level(expression: str, operator: str) -> list[str]:
    """Split an SPDX-style expression without splitting parenthesized terms."""
    parts: list[str] = []
    depth = 0
    start = 0
    index = 0
    token = f" {operator} "
    while index <= len(expression) - len(token):
        char = expression[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return []
        if depth == 0 and expression.startswith(token, index):
            parts.append(expression[start:index].strip())
            index += len(token)
            start = index
            continue
        index += 1
    if depth != 0:
        return []
    parts.append(expression[start:].strip())
    return parts if all(parts) else []


def _has_balanced_outer_parentheses(expression: str) -> bool:
    if not (expression.startswith("(") and expression.endswith(")")):
        return False
    depth = 0
    for index, char in enumerate(expression):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index != len(expression) - 1:
                return False
            if depth < 0:
                return False
    return depth == 0


def is_approved(value: object) -> bool:
    """Accept only expressions whose chosen license path is explicitly approved.

    OR allows a distributor to select one approved alternative. AND requires
    every component to be approved. Unknown, malformed, and unlisted terms fail
    closed; this does not approve any new license identifier.
    """
    expression = _normalize_expression(value)
    if not expression:
        return False
    if _has_balanced_outer_parentheses(expression):
        return is_approved(expression[1:-1])

    # SPDX precedence: AND binds more tightly than OR.
    alternatives = _split_top_level(expression, "OR")
    if len(alternatives) > 1:
        return any(is_approved(part) for part in alternatives)

    conjunction = _split_top_level(expression, "AND")
    if len(conjunction) > 1:
        return all(is_approved(part) for part in conjunction)

    if "(" in expression or ")" in expression:
        return False
    return normalize(expression) in APPROVED_ALIASES


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
        if not is_approved(license_name):
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
