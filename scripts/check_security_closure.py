"""Release gate for the SECURITY_RISK_ACCEPTANCE closure checklist (audit F-12).

The controlled production release workflow runs this script and fails closed
unless every numbered item in the document's "Findings requiring verification
before closure" section is marked CLOSED and every evidence artifact the
section references under docs/ exists in the repository.
"""
from __future__ import annotations

import re
from pathlib import Path

DOC_PATH = Path("docs/SECURITY_RISK_ACCEPTANCE.md")
SECTION_TITLE = "## Findings requiring verification before closure"
CLOSED_MARKER = "CLOSED"


def main() -> int:
    if not DOC_PATH.is_file():
        print(f"FAIL: {DOC_PATH} is missing")
        return 1
    text = DOC_PATH.read_text(encoding="utf-8")
    if SECTION_TITLE not in text:
        print(f"FAIL: section {SECTION_TITLE!r} not found in {DOC_PATH}")
        return 1
    body = text.split(SECTION_TITLE, 1)[1]
    body = body.split("\n## ", 1)[0]

    blocks = [block for block in re.split(r"\n(?=\d+\.\s)", body.strip("\n"))
              if re.match(r"\d+\.\s", block)]
    if not blocks:
        print("FAIL: no numbered closure items found")
        return 1

    failures: list[str] = []
    for block in blocks:
        title = block.splitlines()[0].strip()
        if CLOSED_MARKER not in block:
            failures.append(f"item not CLOSED: {title}")

    for ref in re.findall(r"`(docs/[^`]+)`", body):
        if not Path(ref).is_file():
            failures.append(f"missing evidence file: {ref}")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        print(
            f"Security-acceptance closure check failed ({len(failures)} item(s)); "
            "production release must not proceed."
        )
        return 1
    print(
        f"OK: all {len(blocks)} closure item(s) CLOSED; "
        "referenced evidence files present."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
