"""Fail-closed production security evidence and live dependency audit gate."""
from __future__ import annotations

import json
import posixpath
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

DOC_PATH = Path("docs/SECURITY_RISK_ACCEPTANCE.md")
SECTION_TITLE = "## Findings requiring verification before closure"
CLOSED_MARKER = "CLOSED"
ALLOWED_STATUSES = frozenset({"OPEN", CLOSED_MARKER})
EXPECTED_FINDING_NUMBERS = frozenset({1, 2, 3, 4, 5})
STATUS_LINE = re.compile(r"^(?:(?:[-+]|\d+\.)\s+)?status\s*:\s*(.*?)\s*$", re.IGNORECASE)
EVIDENCE_ROOT = "docs/"
REQUIREMENTS_PATH = Path("requirements.txt")
CURRENT_AUDIT_REPORT = Path("artifacts/security/pip-audit-current.json")

BACKTICK_REF = re.compile(r"\x60(docs/[^\x60]+)\x60")
INLINE_LINK = re.compile(
    r'''\]\(\s*(<[^>\n]*>|[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)(?:\s+(?:"[^"]*"|'[^']*'))?\s*\)'''
)
REFERENCE_DEFINITION = re.compile(
    r"^ {0,3}\[([^\]\n]+)\]:\s*(<[^>\n]*>|\S+)", re.MULTILINE
)
REFERENCE_USE = re.compile(r"!?\[([^\]\n]+)\]\[([^\]\n]*)\]")
URL_SCHEME = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")


def link_evidence_path(destination: str) -> str | None:
    dest = destination.strip()
    if dest.startswith("<") and dest.endswith(">"):
        dest = dest[1:-1].strip()
    dest = unquote(re.split(r"[?#]", dest, maxsplit=1)[0])
    if not dest or URL_SCHEME.match(dest):
        return None
    if dest.startswith("/"):
        candidate = dest.lstrip("/")
    elif dest.startswith(EVIDENCE_ROOT):
        candidate = dest
    else:
        candidate = posixpath.join(DOC_PATH.parent.as_posix(), dest)
    normalized = posixpath.normpath(candidate)
    return normalized if normalized.startswith(EVIDENCE_ROOT) else None


def item_statuses(block: str) -> list[str]:
    statuses = []
    for line in block.splitlines():
        match = STATUS_LINE.match(re.sub(r"[*_\x60]", "", line).strip())
        if match:
            statuses.append(match.group(1))
    return statuses


def is_closed(block: str) -> bool:
    statuses = item_statuses(block)
    return bool(statuses) and all(status == CLOSED_MARKER for status in statuses)


def referenced_evidence_paths(body: str, document: str | None = None) -> list[str]:
    refs = list(BACKTICK_REF.findall(body))
    destinations = INLINE_LINK.findall(body)
    definitions = {
        label.strip().casefold(): destination
        for label, destination in REFERENCE_DEFINITION.findall(document or body)
    }
    for link_text, reference_label in REFERENCE_USE.findall(body):
        label = reference_label.strip() or link_text.strip()
        destination = definitions.get(label.casefold())
        if destination is not None:
            destinations.append(destination)
    for destination in destinations:
        path = link_evidence_path(destination)
        if path is not None:
            refs.append(path)
    return list(dict.fromkeys(refs))


def audit_current_dependencies() -> tuple[bool, str]:
    """Run pip-audit now; never authorize a release from a dated report alone."""
    if not REQUIREMENTS_PATH.is_file():
        return False, f"production requirements file is missing: {REQUIREMENTS_PATH}"
    CURRENT_AUDIT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    CURRENT_AUDIT_REPORT.unlink(missing_ok=True)
    # The executable and all options are fixed; REQUIREMENTS_PATH is a
    # repository-controlled constant (not request or environment input).
    # Keep the argv literal at the call site so static analyzers can inspect it.
    # shell=False (the default) ensures no shell expansion or command parsing.
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "-r",
                str(REQUIREMENTS_PATH),
                "--format",
                "json",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return False, f"could not execute pip-audit: {exc}"
    try:
        report = json.loads(result.stdout)
    except (TypeError, json.JSONDecodeError):
        detail = result.stderr.strip() or result.stdout.strip() or "no JSON output"
        return False, f"pip-audit did not produce valid JSON: {detail}"
    if not isinstance(report, dict) or not isinstance(report.get("dependencies"), list):
        return False, "pip-audit JSON has no dependencies array"
    dependencies = report["dependencies"]
    if not dependencies or any(
        not isinstance(item, dict)
        or not isinstance(item.get("name"), str)
        or not isinstance(item.get("version"), str)
        or not isinstance(item.get("vulns"), list)
        for item in dependencies
    ):
        return False, "pip-audit JSON contains an empty or malformed dependency inventory"
    CURRENT_AUDIT_REPORT.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    vulnerability_count = sum(len(item["vulns"]) for item in dependencies)
    if result.returncode != 0 or vulnerability_count:
        return False, (
            f"current dependency audit failed: exit={result.returncode}, "
            f"packages={len(dependencies)}, vulnerabilities={vulnerability_count}; "
            f"report={CURRENT_AUDIT_REPORT}"
        )
    return True, (
        f"current dependency audit passed: packages={len(dependencies)}, "
        f"vulnerabilities=0; report={CURRENT_AUDIT_REPORT}"
    )


def _item_number(block: str) -> int | None:
    """Return the leading Markdown ``N.`` number, normalized as an integer."""
    lines = block.splitlines()
    if not lines:
        return None
    match = re.match(r"^ {0,3}(\d+)\.\s", lines[0])
    return int(match.group(1)) if match else None


def main(argv: list[str] | None = None) -> int:
    """Run the closure gate.

    Default (fail-closed production gate): every numbered item must carry a
    ``Status: CLOSED`` line, every referenced ``docs/`` evidence file must
    exist, no item number may repeat, and a live ``pip-audit`` must report zero
    vulnerabilities. Used by the production-release and deploy workflows.

    ``--structure-only``: skip the live pip-audit and allow ``Status: OPEN``
    (reported as info, not a failure). Still fails on duplicate item numbers,
    missing/malformed status lines, and missing evidence files. Used by the PR
    CI job so the closure document's structural integrity is checked on every
    pull request without forcing every OPEN item closed or running the slow
    live audit (the live audit remains a release-gate concern).
    """
    args = sys.argv[1:] if argv is None else argv
    structure_only = "--structure-only" in args

    if not DOC_PATH.is_file():
        print(f"FAIL: {DOC_PATH} is missing")
        return 1
    text = DOC_PATH.read_text(encoding="utf-8")
    if SECTION_TITLE not in text:
        print(f"FAIL: section {SECTION_TITLE!r} not found in {DOC_PATH}")
        return 1
    body = text.split(SECTION_TITLE, 1)[1].split("\n## ", 1)[0]
    # Markdown permits up to three leading spaces before a top-level
    # ordered-list marker. Split each marker so indented duplicates cannot be
    # swallowed into the preceding item's block.
    blocks = [
        block
        for block in re.split(r"(?m)(?=^ {0,3}\d+\.\s)", body.strip("\n"))
        if _item_number(block) is not None
    ]
    if not blocks:
        print("FAIL: no numbered closure items found")
        return 1

    failures: list[str] = []
    open_items: list[str] = []
    seen_numbers: dict[str, str] = {}
    for block in blocks:
        title = block.splitlines()[0].strip()
        number = _item_number(block)
        if number is None:
            failures.append(f"closure item has no valid leading number: {title!r}")
        elif number in seen_numbers:
            failures.append(
                f"duplicate closure item {number}: {title!r} repeats "
                f"{seen_numbers[number]!r}"
            )
        else:
            seen_numbers[number] = title

        statuses = item_statuses(block)
        if len(statuses) != 1 or statuses[0].strip() not in ALLOWED_STATUSES:
            failures.append(
                f"item must contain exactly one Status: OPEN or Status: CLOSED line: {title}"
            )
        elif statuses[0].strip() == "OPEN":
            if structure_only:
                open_items.append(title)
            else:
                failures.append(
                    f"item not CLOSED (needs a 'Status: {CLOSED_MARKER}' line): {title}"
                )
    missing_numbers = EXPECTED_FINDING_NUMBERS - set(seen_numbers)
    unexpected_numbers = set(seen_numbers) - EXPECTED_FINDING_NUMBERS
    if missing_numbers:
        failures.append(
            "missing required closure item(s): "
            + ", ".join(str(number) for number in sorted(missing_numbers))
        )
    if unexpected_numbers:
        failures.append(
            "unexpected closure item number(s): "
            + ", ".join(str(number) for number in sorted(unexpected_numbers))
        )

    for ref in referenced_evidence_paths(body, text):
        if not Path(ref).is_file():
            failures.append(f"missing evidence file: {ref}")

    if not structure_only:
        audit_ok, audit_message = audit_current_dependencies()
        print(("OK: " if audit_ok else "FAIL: ") + audit_message)
        if not audit_ok:
            failures.append(audit_message)

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        label = "structure check" if structure_only else "security-acceptance closure check"
        print(
            f"{label} failed ({len(failures)} issue(s)); "
            "production release must not proceed."
        )
        return 1

    if structure_only:
        print(
            f"OK (structure-only): {len(blocks)} closure item(s), "
            f"{len(seen_numbers)} unique; {len(open_items)} OPEN item(s) "
            "(production gate will block until CLOSED)."
        )
        for title in open_items:
            print(f"  OPEN: {title}")
    else:
        print(
            f"OK: all {len(blocks)} closure item(s) CLOSED; evidence exists; "
            "live audit passed."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
