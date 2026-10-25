#!/usr/bin/env python3
"""
RES-010 through RES-017 -- Rescue execution & case lifecycle audit.

Static analyzer for the NLC platform's rescue workflow code. Identifies
gaps in: engagement context, contract tests, lifecycle status naming,
fail-safe behaviour, closure conditions, planner parity, plan determinism,
and audit trail completeness.

Findings emitted:
    RES-010  Rescue actions may lack engagement/case context
    RES-011  Rescue->engagement function call needs contract tests
    RES-012  Lifecycle status COMPLETED vs COMPLETE naming drift
    RES-013  Unmapped actionable findings must fail safely & visibly
    RES-014  Closure must be based on verified conditions, not elapsed time
    RES-015  Legacy fixed-step generator vs canonical planner divergence
    RES-016  Plan ordering/prerequisites/dedup/aggregation deterministic tests
    RES-017  Audit history must record finding/rule_version/action/actor/
             evidence/outcome

Also splits RES-001~009 (legacy "rescue tests skipped" combined entry) into
individual rows in the report so each can be tracked separately.

Usage:
    python scripts/verify_rescue_lifecycle.py /path/to/nlc_platform_clean
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


def collect_py_files(repo_root: Path) -> list[Path]:
    targets = []
    for sub in ("app", "canonical_architecture", "tests"):
        d = repo_root / sub
        if d.exists():
            targets.extend(p for p in d.rglob("*.py"))
    return sorted(targets)


# Legacy RES-001 through RES-009 -- split into individual rows
LEGACY_RES_ITEMS = {
    "RES-001": "Rescue test for engagement creation skipped",
    "RES-002": "Rescue test for step update skipped",
    "RES-003": "Rescue test for closure verification skipped",
    "RES-004": "Rescue test for plan aggregation skipped",
    "RES-005": "Rescue test for audit trail skipped",
    "RES-006": "Rescue test for cross-tenant access skipped",
    "RES-007": "Rescue test for legacy planner parity skipped",
    "RES-008": "Rescue test for unmapped findings skipped",
    "RES-009": "Rescue test for plan dedup skipped",
}


def check_legacy_split(repo_root: Path, findings: list[Finding]) -> None:
    """H: split RES-001~009 into individual rows."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    # look for skipped tests with @pytest.mark.skip or @unittest.skip
    skipped_rescue_tests = []
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "rescue" not in text.lower():
            continue
        for m in re.finditer(r"@(?:pytest\.mark\.skip|unittest\.skip)\([^)]*\)\s*\n(?:async\s+)?def\s+(\w+)", text):
            skipped_rescue_tests.append((p, m.group(1)))
        # also flag skip without reason
        for m in re.finditer(r"@pytest\.mark\.skip\s*\n(?:async\s+)?def\s+(\w+)", text):
            skipped_rescue_tests.append((p, m.group(1)))

    # For each legacy RES item, check if there's a related skipped test
    for rid, desc in LEGACY_RES_ITEMS.items():
        # Map by keyword
        keyword_map = {
            "RES-001": "engagement",
            "RES-002": "step",
            "RES-003": "closure",
            "RES-004": "aggregat",
            "RES-005": "audit",
            "RES-006": "tenant",
            "RES-007": "parity",
            "RES-008": "unmapped",
            "RES-009": "dedup",
        }
        kw = keyword_map[rid]
        matching = [(p, name) for p, name in skipped_rescue_tests if kw in name.lower()]
        if matching:
            for p, name in matching[:3]:
                findings.append(Finding(
                    rid, str(p), 0, "WARN",
                    f"Skipped rescue test detected: {name} (matches {rid} keyword '{kw}').",
                    "Remove the skip decorator and ensure the test runs against a real DB.",
                ))
        else:
            findings.append(Finding(
                rid, "(tests)", 0, "WARN",
                f"{rid}: {desc}. No skipped test found matching keyword '{kw}', but no test "
                f"was found either -- the test may simply not exist.",
                "Add the missing test case.",
            ))


def check_res_010(repo_root: Path, findings: list[Finding]) -> None:
    """RES-010: rescue actions may lack engagement/case context when converted from a finding."""
    files = collect_py_files(repo_root)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Look for `create_rescue_plan(` or `rescue_from_finding(` without engagement_id
        for m in re.finditer(r"(?:create_rescue_plan|rescue_from_finding|generate_rescue_plan)\s*\(([^)]*)\)", text):
            args = m.group(1)
            if "engagement" not in args.lower() and "case_id" not in args.lower():
                lineno = text[:m.start()].count("\n") + 1
                findings.append(Finding(
                    "RES-010", str(p), lineno, "WARN",
                    f"Rescue plan creation call does not pass engagement_id or case_id: `{m.group(0)[:100]}`",
                    "Add `engagement_id` parameter to every rescue creation call so the resulting "
                    "plan is linked to an authenticated engagement record.",
                ))


def check_res_011(repo_root: Path, findings: list[Finding]) -> None:
    """RES-011: rescue->engagement function call needs contract tests."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    contract_test_found = False
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"def\s+test_.*rescue.*engagement|def\s+test_.*engagement.*rescue", text, re.I):
            contract_test_found = True
            break
    if not contract_test_found:
        findings.append(Finding(
            "RES-011", "(tests)", 0, "FAIL",
            "No contract test for the rescue->engagement function call found.",
            "Add tests/unit/test_rescue_engagement_contract.py: stub the function with each "
            "argument type combination and assert the resulting engagement row is correctly "
            "linked to the originating finding.",
        ))


def check_res_012(repo_root: Path, findings: list[Finding]) -> None:
    """RES-012: lifecycle status naming -- COMPLETED vs COMPLETE drift."""
    files = collect_py_files(repo_root)
    completed_refs = []
    complete_refs = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'\b(RescueState|RescueStatus|rescue_status|status)\s*[=:]\s*["\']?(COMPLETED|COMPLETE)["\']?', text):
            status = m.group(2)
            lineno = text[:m.start()].count("\n") + 1
            if status == "COMPLETED":
                completed_refs.append((p, lineno))
            else:
                complete_refs.append((p, lineno))
    if completed_refs and complete_refs:
        findings.append(Finding(
            "RES-012", str(completed_refs[0][0]), completed_refs[0][1], "FAIL",
            f"Both COMPLETED ({len(completed_refs)} refs) and COMPLETE ({len(complete_refs)} refs) "
            f"are used in the codebase. Consumers may parse one and miss the other.",
            "Pick ONE: standardize on `COMPLETED` (matches the `is_*ed` past-tense convention). "
            "Add an alias `COMPLETE = COMPLETED` to the enum for backward compatibility.",
        ))


def check_res_013(repo_root: Path, findings: list[Finding]) -> None:
    """RES-013: unmapped actionable findings must fail safely and visibly."""
    files = collect_py_files(repo_root)
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # look for KeyError swallowing or default empty list on lookup of rescue action
        for m in re.finditer(r"(?:rescue_action|action_map|RESCUE_ACTIONS)\.get\([^,]+,\s*(?:None|\[\])\)", text):
            lineno = text[:m.start()].count("\n") + 1
            findings.append(Finding(
                "RES-013", str(p), lineno, "WARN",
                f"Rescue action lookup silently returns None/[] on miss: `{m.group(0)[:80]}`. "
                f"Unmapped actionable findings disappear.",
                "Replace with explicit lookup that raises a logged exception when a "
                "NON_COMPLIANT/RED/BLACK finding has no rescue action mapped.",
            ))


def check_res_014(repo_root: Path, findings: list[Finding]) -> None:
    """RES-014: closure based on verified conditions, not elapsed time."""
    files = collect_py_files(repo_root)
    suspicious_closures = []
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Look for `if (datetime.now() - plan.created_at).days > N` patterns
        for m in re.finditer(r"\(datetime\.now\(\)[^)]*\)\.days\s*>\s*\d+|elapsed.*>\s*\d+|timedelta\([^)]*\).*>\s*timedelta", text):
            lineno = text[:m.start()].count("\n") + 1
            # check if this is near a closure decision
            ctx = text[max(0, m.start() - 400):m.end() + 200]
            if "close" in ctx.lower() or "complete" in ctx.lower() or "resolve" in ctx.lower():
                suspicious_closures.append((p, lineno, m.group(0)[:80]))
    for p, ln, snippet in suspicious_closures:
        findings.append(Finding(
            "RES-014", str(p), ln, "WARN",
            f"Rescue closure appears gated on elapsed time: `{snippet}`. Elapsed time is NOT "
            f"a verification condition.",
            "Replace with closure_condition checks: e.g. closure requires "
            "AGM-001 == RuleState.COMPLIANT (re-evaluated against fresh evidence), not just "
            "30 days passed.",
        ))


def check_res_015(repo_root: Path, findings: list[Finding]) -> None:
    """RES-015: legacy fixed-step generator vs canonical planner may diverge."""
    canonical = repo_root / "canonical_architecture" / "statutory_rescue.py"
    legacy_dir = repo_root / "app" / "services"
    legacy_file = None
    if legacy_dir.exists():
        for cand in ("rescue_service.py", "rescue_planner.py", "rescue.py"):
            p = legacy_dir / cand
            if p.exists():
                legacy_file = p
                break
    if not (canonical.exists() and legacy_file):
        return
    canonical_text = canonical.read_text(encoding="utf-8", errors="ignore")
    legacy_text = legacy_file.read_text(encoding="utf-8", errors="ignore")
    # check if a parity test exists
    test_dir = repo_root / "tests"
    parity_test = False
    if test_dir.exists():
        for p in test_dir.rglob("*.py"):
            try:
                t = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if "rescue" in t.lower() and ("parity" in t.lower() or "legacy" in t.lower() and "canonical" in t.lower()):
                parity_test = True
                break
    if not parity_test:
        findings.append(Finding(
            "RES-015", f"{legacy_file.name} <-> {canonical.name}", 0, "WARN",
            "Both legacy rescue service and canonical rescue planner exist. No parity test found.",
            "Add tests/unit/test_rescue_planner_parity.py: for each rule ID with a rescue action, "
            "generate plans from both legacy and canonical generators and assert the resulting "
            "step sequences are identical.",
        ))


def check_res_016(repo_root: Path, findings: list[Finding]) -> None:
    """RES-016: plan ordering/prerequisites/dedup/aggregation need deterministic tests."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    deterministic_test_keywords = ["rescue", ("ordering" in str(None) or "order"), "prereq",
                                   "dedup", "aggregat", "deterministic"]
    found = False
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "rescue" in text.lower() and any(k in text.lower() for k in ("ordering", "prereq", "dedup", "aggregat", "deterministic")):
            found = True
            break
    if not found:
        findings.append(Finding(
            "RES-016", "(tests)", 0, "FAIL",
            "No deterministic test for rescue plan ordering/prerequisites/dedup/aggregation.",
            "Add a test that builds a plan from a multi-finding input (e.g. AGM-001, AGM-002, "
            "AUD-001, AR-001) and asserts: (a) deduplication removes redundant steps, "
            "(b) AGM-001 step precedes AGM-002 step, (c) prerequisites are honoured, "
            "(d) plan is reproducible from the same input.",
        ))


def check_res_017(repo_root: Path, findings: list[Finding]) -> None:
    """RES-017: audit history must record finding/rule_version/action/actor/evidence/outcome."""
    models_dir = repo_root / "app" / "models"
    if not models_dir.exists():
        return
    # Look for RescueAuditLog or similar table
    audit_model_paths = []
    for p in models_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"class\s+\w*(Rescue|RescueAudit|RescueAction)\w*Log\w*\(", text):
            audit_model_paths.append(p)
    if not audit_model_paths:
        findings.append(Finding(
            "RES-017", "(models)", 0, "FAIL",
            "No rescue audit log table detected in app/models.",
            "Create a rescue_audit_log table with columns: id, rescue_plan_id, finding_id, "
            "rule_id, rule_version, action_performed, actor_user_id, evidence_ref, outcome, "
            "timestamp.",
        ))
        return
    required_columns = ["finding_id", "rule_id", "rule_version", "action_performed",
                        "actor_user_id", "evidence", "outcome", "timestamp"]
    for p in audit_model_paths:
        text = p.read_text(encoding="utf-8", errors="ignore")
        missing_cols = [c for c in required_columns if c not in text.replace('"', '').replace("'", '')]
        if missing_cols:
            findings.append(Finding(
                "RES-017", str(p), 0, "WARN",
                f"Rescue audit log model in {p.name} appears to be missing columns: {missing_cols}.",
                "Add the missing columns. Without rule_version, historical audits cannot be "
                "reproduced after rule definitions change.",
            ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/rescue_lifecycle_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC Rescue Lifecycle Audit ===")
    print(f"Repo: {repo_root}")
    print()

    findings: list[Finding] = []
    check_legacy_split(repo_root, findings)
    check_res_010(repo_root, findings)
    check_res_011(repo_root, findings)
    check_res_012(repo_root, findings)
    check_res_013(repo_root, findings)
    check_res_014(repo_root, findings)
    check_res_015(repo_root, findings)
    check_res_016(repo_root, findings)
    check_res_017(repo_root, findings)

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