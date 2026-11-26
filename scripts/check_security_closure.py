"""Release gate for the SECURITY_RISK_ACCEPTANCE closure checklist (audit F-12).

Both production deployment workflows run this script and fail closed
unless every numbered item in the document's "Findings requiring verification
before closure" section carries a ``Status: CLOSED`` line (the status value
must be exactly ``CLOSED``; ``NOT CLOSED``, ``OPEN`` or a missing status all
fail) and every evidence artifact the section references under docs/ exists in
the repository. References are
backticked docs/ paths and Markdown link destinations (inline and reference
style) that resolve under docs/.
"""
from __future__ import annotations

import posixpath
import re
from pathlib import Path
from urllib.parse import unquote

DOC_PATH = Path("docs/SECURITY_RISK_ACCEPTANCE.md")
SECTION_TITLE = "## Findings requiring verification before closure"
CLOSED_MARKER = "CLOSED"
STATUS_LINE = re.compile(r"^(?:(?:[-+]|\d+\.)\s+)?status\s*:\s*(.*?)\s*$", re.IGNORECASE)
EVIDENCE_ROOT = "docs/"

BACKTICK_REF = re.compile(r"`(docs/[^`]+)`")
INLINE_LINK = re.compile(
    r"\]\(\s*(<[^>\n]*>|[^()\s]*(?:\([^()\s]*\)[^()\s]*)*)(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)"
)
REFERENCE_LINK = re.compile(r"^ {0,3}\[[^\]\n]+\]:\s*(<[^>\n]*>|\S+)", re.MULTILINE)
URL_SCHEME = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*:|//)")


def link_evidence_path(destination: str) -> str | None:
    """Map a Markdown link destination to a repo-relative docs/ path, if it is one.

    External URLs and pure anchors are not evidence files. As with backticked
    references, a destination starting with docs/ is repo-root relative; any other
    relative destination is resolved against the directory of DOC_PATH.
    """
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
    """Return the value of every ``Status:`` line in a closure item, markup removed."""
    statuses = []
    for line in block.splitlines():
        match = STATUS_LINE.match(re.sub(r"[*_`]", "", line).strip())
        if match:
            statuses.append(match.group(1))
    return statuses


def is_closed(block: str) -> bool:
    statuses = item_statuses(block)
    return bool(statuses) and all(status == CLOSED_MARKER for status in statuses)


def referenced_evidence_paths(body: str) -> list[str]:
    refs = list(BACKTICK_REF.findall(body))
    destinations = INLINE_LINK.findall(body) + REFERENCE_LINK.findall(body)
    for destination in destinations:
        path = link_evidence_path(destination)
        if path is not None:
            refs.append(path)
    return list(dict.fromkeys(refs))


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
        if not is_closed(block):
            failures.append(f"item not CLOSED (needs a 'Status: {CLOSED_MARKER}' line): {title}")

    for ref in referenced_evidence_paths(body):
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
