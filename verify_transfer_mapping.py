#!/usr/bin/env python3
"""
TR-007 through TR-012 -- Transfer & service-to-engine mapping audit.

Static analyzer that flags gaps in transfer-rule evaluation, especially
around Form 117, AoA restrictions, board approval fields, and the
bool() collapse of missing approval evidence.

Findings emitted:
    TR-007  Form 117 marked as None or TODO without actual data source
    TR-008  Transfer-level AoA restriction vs company-level AoA restriction
            not reconciled
    TR-009  No service-level regression proves DB->engine field meaning
    TR-010  board_approval and board_approval_obtained are separate fields
    TR-011  bool(...) collapse of missing/contradictory approval evidence
    TR-012  Test design gap -- tests do not distinguish AoA violation /
            restriction applies / missing evidence

Usage:
    python scripts/verify_transfer_mapping.py /path/to/nlc_platform_clean
"""
from __future__ import annotations

import sys
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
import argparse
import ast
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Finding:
    check_id: str
    file: str
    line: int
    severity: str
    detail: str
    suggested_fix: str = ""


def find_python_files(repo_root: Path) -> list[Path]:
    targets = []
    for sub in ("app", "canonical_architecture", "tests"):
        d = repo_root / sub
        if d.exists():
            targets.extend(p for p in d.rglob("*.py"))
    return sorted(targets)


def check_tr_007(repo_root: Path, findings: list[Finding]) -> None:
    """TR-007: Form 117 = None is not a fix; flag TODO + None combination."""
    pattern_form_117 = re.compile(r"form_117", re.I)
    pattern_none = re.compile(r"form_117.*=\s*None|form_117_filed.*=\s*None|form_117.*None", re.I)
    pattern_todo = re.compile(r"#\s*TODO|#\s*FIXME|#\s*HACK", re.I)
    pattern_unresolved = re.compile(r"#\s*TODO.*form_117|form_117.*TODO", re.I)
    for p in find_python_files(repo_root):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        lines = text.splitlines()
        for i, ln in enumerate(lines, start=1):
            if not pattern_form_117.search(ln):
                continue
            if pattern_none.search(ln):
                # check immediate context for TODO
                ctx = "\n".join(lines[max(0, i - 4):i + 4])
                if pattern_todo.search(ctx):
                    findings.append(Finding(
                        "TR-007", str(p), i, "FAIL",
                        f"Form 117 set to None near a TODO comment -- not an actual fix: {ln.strip()}",
                        "Implement the real Form 117 data source (lookup against RJSC filings table "
                        "or NLC import). Use UNKNOWN until verified, do NOT default to None.",
                    ))
                else:
                    findings.append(Finding(
                        "TR-007", str(p), i, "WARN",
                        f"Form 117 assigned None without obvious TODO nearby -- confirm at runtime "
                        f"whether None means UNKNOWN or NOT_APPLICABLE. {ln.strip()}",
                        "Add explicit comment: # UNKNOWN until RJSC verified OR # NOT_APPLICABLE.",
                    ))


def check_tr_008(repo_root: Path, findings: list[Finding]) -> None:
    """TR-008: transfer-level AoA restriction vs company-level restriction not reconciled."""
    # Look for both transfer.restriction / company.aoa_restriction references
    transfer_ref = re.compile(r"transfer[._]restriction|transfer_restriction|share_transfer.*restriction", re.I)
    company_ref = re.compile(r"company[._]aoa|company_aoa|aoa_restriction", re.I)
    found_transfer = []
    found_company = []
    for p in find_python_files(repo_root):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, ln in enumerate(text.splitlines(), start=1):
            if transfer_ref.search(ln):
                found_transfer.append((p, i, ln.strip()))
            if company_ref.search(ln):
                found_company.append((p, i, ln.strip()))
    if found_transfer and found_company:
        # They appear in different files / lines -- risk of drift
        # Check if any file uses BOTH and reconciles them
        reconciled = False
        for p_t, _, _ in found_transfer:
            for p_c, _, _ in found_company:
                if p_t == p_c:
                    reconciled = True
                    break
        if not reconciled:
            findings.append(Finding(
                "TR-008", str(found_transfer[0][0]), found_transfer[0][1], "WARN",
                f"Transfer-level restriction ({len(found_transfer)} refs) and company-level AoA "
                f"restriction ({len(found_company)} refs) appear in different files. No visible "
                f"reconciliation logic.",
                "Add an explicit reconciliation: at the start of evaluate(), if "
                "transfer.restriction is None, fall back to company.aoa_restriction; if both are "
                "set, prefer the transfer-level value with an audit note.",
            ))


def check_tr_009(repo_root: Path, findings: list[Finding]) -> None:
    """TR-009: no service-level regression test proves DB->engine field meaning."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    regression_tests = []
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Looking for tests that (a) create a Transfer row in DB and (b) call engine.evaluate()
        if "Transfer(" in text and "evaluate(" in text and ("session" in text.lower() or "db" in text.lower()):
            regression_tests.append(p)
    if not regression_tests:
        findings.append(Finding(
            "TR-009", "(tests)", 0, "FAIL",
            "No service-level regression test found that (a) persists a Transfer row to the DB and "
            "(b) calls engine.evaluate() to verify the fields arrive at the engine with intended "
            "meaning.",
            "Add tests/unit/test_transfer_db_to_engine.py: persist a Transfer with each combo of "
            "{restriction=True/False, board_approval=True/False/None} and assert the resulting "
            "Finding matches expectation for each.",
        ))


def check_tr_010(repo_root: Path, findings: list[Finding]) -> None:
    """TR-010: board_approval and board_approval_obtained are separate fields."""
    files = find_python_files(repo_root)
    approval_writes = defaultdict(list)  # field_name -> list of (file, line)
    approval_reads = defaultdict(list)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for i, ln in enumerate(text.splitlines(), start=1):
            # tests/models write: e.g. board_approval=True
            if re.search(r"\bboard_approval_obtained\b", ln):
                approval_writes["board_approval_obtained"].append((str(p), i, ln.strip()))
            if re.search(r"\bboard_approval\b(?!\w)", ln):  # not _obtained
                approval_writes["board_approval"].append((str(p), i, ln.strip()))
    # Check if both are used in the codebase
    if approval_writes["board_approval"] and approval_writes["board_approval_obtained"]:
        # Check if they're used consistently in the same file
        files_using_only_board_approval = {fp for fp, _, _ in approval_writes["board_approval"]} - \
                                          {fp for fp, _, _ in approval_writes["board_approval_obtained"]}
        files_using_only_obtained = {fp for fp, _, _ in approval_writes["board_approval_obtained"]} - \
                                     {fp for fp, _, _ in approval_writes["board_approval"]}
        if files_using_only_board_approval and files_using_only_obtained:
            findings.append(Finding(
                "TR-010", "?", 0, "FAIL",
                f"`board_approval` and `board_approval_obtained` are both used in the codebase but "
                f"in different files. Tests may set one while the engine reads the other.\n"
                f"  Files using only `board_approval`: {sorted(files_using_only_board_approval)[:3]}\n"
                f"  Files using only `board_approval_obtained`: {sorted(files_using_only_obtained)[:3]}",
                "Pick ONE field name and use it everywhere. The ORM column name should match the "
                "attribute name on the Transfer model and the field written in tests.",
            ))


def check_tr_011(repo_root: Path, findings: list[Finding]) -> None:
    """TR-011: bool() collapse of missing/contradictory approval evidence."""
    files = find_python_files(repo_root)
    suspicious_bools = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Look for `bool(...board_approval...)` or `if board_approval:`
        for m in re.finditer(r"bool\s*\([^)]*board_approval|if\s+board_approval(?:_obtained)?\s*:", text):
            lineno = text[:m.start()].count("\n") + 1
            suspicious_bools.append((p, lineno, m.group(0)))
        # Also flag `if not board_approval: NON_COMPLIANT`
        for m in re.finditer(r"if\s+not\s+board_approval(?:_obtained)?\s*:[^\n]*\n[^\n]*NON_COMPLIANT", text):
            lineno = text[:m.start()].count("\n") + 1
            suspicious_bools.append((p, lineno, m.group(0)[:80]))
    for p, ln, snippet in suspicious_bools:
        findings.append(Finding(
            "TR-011", str(p), ln, "WARN",
            f"Approval evidence collapsed via truthiness: `{snippet}`. None (unknown) and False "
            "(confirmed no) become indistinguishable.",
            "Replace `if not board_approval:` with explicit 3-valued logic: "
            "if board_approval is None -> UNKNOWN; elif board_approval is False -> NON_COMPLIANT; "
            "else COMPLIANT.",
        ))


def check_tr_012(repo_root: Path, findings: list[Finding]) -> None:
    """TR-012: tests must distinguish AoA violation vs restriction applies vs missing evidence."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    relevant_tests = []
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "TR-" in text or "transfer" in text.lower() or "AoA" in text or "aoa_restriction" in text:
            relevant_tests.append(p)
    if not relevant_tests:
        findings.append(Finding(
            "TR-012", "(tests)", 0, "WARN",
            "No transfer-rule tests detected by heuristic search.",
        ))
        return
    # For each test file, check the three required scenarios
    for p in relevant_tests:
        text = p.read_text(encoding="utf-8", errors="ignore")
        has_violation_case = bool(re.search(r"restriction.*=.*True.*violation|violates.*aoa|transfer.*void", text, re.I))
        has_restriction_applies = bool(re.search(r"restriction.*applies|pre_empt|right_of_first_refusal", text, re.I))
        has_missing_evidence = bool(re.search(r"board_approval.*None|approval.*None|unknown.*transfer|transfer.*unknown", text, re.I))
        missing = []
        if not has_violation_case:
            missing.append("confirmed AoA violation case")
        if not has_restriction_applies:
            missing.append("restriction applies (non-violating) case")
        if not has_missing_evidence:
            missing.append("missing approval evidence case")
        if missing:
            findings.append(Finding(
                "TR-012", str(p), 0, "WARN",
                f"Transfer test in {p.name} does not clearly cover: {', '.join(missing)}.",
                "Add explicit test cases for each scenario: (a) restriction violated -> "
                "NON_COMPLIANT + BLACK; (b) restriction present but complied with -> COMPLIANT; "
                "(c) approval evidence missing -> UNKNOWN (0 pts).",
            ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/transfer_mapping_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC Transfer Mapping Audit ===")
    print(f"Repo: {repo_root}")
    print()

    findings: list[Finding] = []
    check_tr_007(repo_root, findings)
    check_tr_008(repo_root, findings)
    check_tr_009(repo_root, findings)
    check_tr_010(repo_root, findings)
    check_tr_011(repo_root, findings)
    check_tr_012(repo_root, findings)

    by_check: dict[str, list[Finding]] = defaultdict(list)
    for f in findings:
        by_check[f.check_id].append(f)

    print(f"=== SUMMARY ===")
    for cid in sorted(by_check):
        rows = by_check[cid]
        fail = sum(1 for r in rows if r.severity == "FAIL")
        warn = sum(1 for r in rows if r.severity == "WARN")
        info = sum(1 for r in rows if r.severity == "INFO")
        print(f"  {cid}: FAIL={fail} WARN={warn} INFO={info}")
    print()

    for cid in sorted(by_check):
        print(f"--- {cid} ---")
        for r in by_check[cid]:
            marker = {"FAIL": "XX", "WARN": "!!", "INFO": "--", "PASS": "OK"}.get(r.severity, "??")
            print(f"[{marker}] {r.file}:{r.line}  {r.detail}")
            if r.suggested_fix:
                print(f"      -> FIX: {r.suggested_fix}")
        print()

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "repo": str(repo_root),
        "findings": [asdict(f) for f in findings],
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"JSON report: {args.output}")

    fail_total = sum(1 for f in findings if f.severity == "FAIL")
    return 0 if fail_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())