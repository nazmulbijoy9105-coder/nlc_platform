#!/usr/bin/env python3
"""
Section L -- Documents, AI approval & commercial workflows audit.

Covers:
    COM-001  AI-generated legal drafts must not be sent/filed without required human approval
    COM-002  Approval/rejection must be attributable + recorded in audit trail
    COM-003  Document access/download must enforce same tenant isolation as listing
    COM-004  Rescue engagement create/assign/pay/close must enforce valid lifecycle transitions
    COM-005  Commercial package entitlements must be checked server-side
    COM-006  Deadline notifications need idempotency + delivery-failure handling
    COM-007  Client-visible compliance reports must correspond to correct company/snapshot/version

Usage:
    python scripts/verify_commercial.py /path/to/nlc_platform_clean
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


def check_com_001(repo_root: Path, findings: list[Finding]) -> None:
    """COM-001: AI-generated legal drafts need human approval before send/file."""
    ai_files = []
    for p in collect_py_files(repo_root):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"ai_generated|llm_generated|draft_generation|generate_draft|openai|claude|anthropic|zai|glm", text, re.I):
            ai_files.append(p)
    if not ai_files:
        findings.append(Finding(
            "COM-001", "?", 0, "INFO",
            "No AI draft generation code detected. May not apply.",
        ))
        return
    # Check for approval gate
    has_approval_gate = False
    for p in ai_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"approval_status|approved_by|is_approved|requires_approval|approval_required", text, re.I):
            has_approval_gate = True
            break
    if not has_approval_gate:
        findings.append(Finding(
            "COM-001", str(ai_files[0]), 0, "FAIL",
            "AI draft generation detected but no approval-status gate. Drafts may be sent/filed "
            "without human review.",
            "Add an `approval_status` column to document_versions: PENDING / APPROVED / REJECTED. "
            "Block send/file endpoints unless approval_status == APPROVED.",
        ))


def check_com_002(repo_root: Path, findings: list[Finding]) -> None:
    """COM-002: approval/rejection attributable + recorded in audit trail."""
    py_files = collect_py_files(repo_root)
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # look for approve/reject endpoints
        if re.search(r"def\s+\w*(approve|reject)\w*\s*\(", text):
            # check if approved_by/actor is recorded
            if not re.search(r"approved_by|rejected_by|actor|user_id.*=.*current_user", text, re.I):
                lineno = text.find("def " + text[text.find("def approve") + 4:text.find("def approve") + 30].split("(")[0])
                findings.append(Finding(
                    "COM-002", str(p), 0, "WARN",
                    f"Approve/reject endpoint in {p.name} does not appear to record "
                    f"approved_by/actor field. Attribution missing.",
                    "Set `document.approved_by = current_user.id` and write an activity_log "
                    "entry: `Approved document X by user Y at timestamp`.",
                ))


def check_com_003(repo_root: Path, findings: list[Finding]) -> None:
    """COM-003: document access/download must enforce tenant isolation."""
    api_dir = repo_root / "app" / "api"
    if not api_dir.exists():
        return
    doc_routes = []
    for p in api_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(p))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                attr = dec.func.attr
                if attr not in {"get", "post"}:
                    continue
                path = "/"
                if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                    path = dec.args[0].value
                func_name = node.name.lower()
                if any(k in func_name for k in ("download", "view", "fetch", "get_file")) or "download" in path or "/file" in path:
                    try:
                        dec_text = ast.unparse(dec)
                        sig_text = ast.unparse(node.args)
                    except Exception:
                        dec_text = sig_text = ""
                    doc_routes.append({
                        "file": str(p), "function": node.name, "path": path,
                        "line": node.lineno, "dec_text": dec_text, "sig_text": sig_text,
                    })
    for r in doc_routes:
        if not any(k in r["dec_text"] or k in r["sig_text"] for k in
                   ("require_company_access", "require_tenant_access", "verify_company_access")):
            findings.append(Finding(
                "COM-003", r["file"], r["line"], "FAIL",
                f"Document access/download endpoint {r['function']} ({r['path']}) lacks "
                f"require_company_access dependency. Cross-tenant document leak risk.",
                "Add `current_company=Depends(require_company_access)` to the endpoint.",
            ))


def check_com_004(repo_root: Path, findings: list[Finding]) -> None:
    """COM-004: rescue engagement create/assign/pay/close must enforce valid lifecycle."""
    py_files = collect_py_files(repo_root)
    has_engagement_lifecycle = False
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "engagement" in text.lower() and (
            "status" in text.lower() and re.search(r"VALID_TRANSITIONS|valid_transitions|allowed_status", text, re.I)
        ):
            has_engagement_lifecycle = True
    if not has_engagement_lifecycle:
        findings.append(Finding(
            "COM-004", "(engagement)", 0, "WARN",
            "No engagement lifecycle state machine detected. Invalid transitions "
            "(e.g. CLOSED -> ASSIGNED) may succeed.",
            "Add a `VALID_ENGAGEMENT_TRANSITIONS` dict and validate every PATCH /engagement "
            "against it.",
        ))


def check_com_005(repo_root: Path, findings: list[Finding]) -> None:
    """COM-005: commercial package entitlements must be checked server-side."""
    py_files = collect_py_files(repo_root)
    has_entitlement_check = False
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"entitlement|check_entitlement|has_package|subscription.*active|feature_available", text, re.I):
            has_entitlement_check = True
            break
    if not has_entitlement_check:
        findings.append(Finding(
            "COM-005", "(commercial)", 0, "FAIL",
            "No server-side entitlement check detected. Frontend-only gating is bypassable.",
            "Add `Depends(require_entitlement('feature_name'))` to every route that produces "
            "premium content / actions.",
        ))


def check_com_006(repo_root: Path, findings: list[Finding]) -> None:
    """COM-006: deadline notifications need idempotency + delivery-failure handling."""
    py_files = collect_py_files(repo_root)
    notification_files = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"send_notification|notify|deadline.*alert|reminder", text, re.I):
            notification_files.append(p)
    if not notification_files:
        return
    has_idempotency = False
    has_failure_handling = False
    for p in notification_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"idempotency_key|notification_id.*unique|already_sent", text, re.I):
            has_idempotency = True
        if re.search(r"retry_count|max_attempts|dead_letter|on_failure", text, re.I):
            has_failure_handling = True
    if not has_idempotency:
        findings.append(Finding(
            "COM-006", str(notification_files[0]), 0, "WARN",
            "Notification code lacks visible idempotency key. Worker restart may re-send "
            "duplicate deadline alerts.",
            "Add a `notification_id` (uuid) per logical notification; check exists before insert.",
        ))
    if not has_failure_handling:
        findings.append(Finding(
            "COM-006", str(notification_files[0]), 0, "WARN",
            "Notification code lacks visible delivery-failure handling. Failed deliveries "
            "may silently drop.",
            "On send failure: increment retry_count; if > 3, write to dead_letter table and "
            "alert ops.",
        ))


def check_com_007(repo_root: Path, findings: list[Finding]) -> None:
    """COM-007: client-visible compliance reports must correspond to correct company/snapshot/version."""
    py_files = collect_py_files(repo_root)
    report_files = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"compliance.*report|generate_report|pdf_report|report_service", text, re.I):
            report_files.append(p)
    if not report_files:
        return
    has_snapshot_ref = False
    has_version_ref = False
    for p in report_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"snapshot_id|evidence_snapshot|snapshot_hash", text, re.I):
            has_snapshot_ref = True
        if re.search(r"engine_version|rule_version|registry_hash", text, re.I):
            has_version_ref = True
    if not has_snapshot_ref:
        findings.append(Finding(
            "COM-007", str(report_files[0]), 0, "WARN",
            "Report service does not appear to bind to an evidence snapshot_id. Report content "
            "may be inconsistent with the snapshot displayed to the client.",
            "Persist evidence snapshot at evaluation time; reference snapshot_id in the report.",
        ))
    if not has_version_ref:
        findings.append(Finding(
            "COM-007", str(report_files[0]), 0, "WARN",
            "Report service does not appear to record rule_engine_version. Same report URL may "
            "render different content over time as rule definitions change.",
            "Stamp every report with engine_version + registry_hash; render the report against "
            "the rule definitions in force at evaluation time.",
        ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/commercial_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC Commercial Workflows Audit ===")
    print(f"Repo: {repo_root}")
    print()

    findings: list[Finding] = []
    check_com_001(repo_root, findings)
    check_com_002(repo_root, findings)
    check_com_003(repo_root, findings)
    check_com_004(repo_root, findings)
    check_com_005(repo_root, findings)
    check_com_006(repo_root, findings)
    check_com_007(repo_root, findings)

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