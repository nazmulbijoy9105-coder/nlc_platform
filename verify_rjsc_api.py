#!/usr/bin/env python3
"""
Section J -- RJSC workflows, API contracts & frontend integration audit.

Covers:
    RJSC-001  Mark-filed operations need explicit company-level authorization
    RJSC-002  Frontend/backend endpoint names may disagree (underscore vs hyphen)
    RJSC-003  Frontend response shape expectations vs backend schema
    RJSC-004  Cross-tenant tests for each RJSC route
    RJSC-005  Filing lifecycle transitions must reject invalid transitions
    RJSC-006  Filing deadlines/dates need consistent timezone semantics
    API-001   Live API rule parity remains unverified (401 from parity check)
    API-002   Every router must have explicit auth/authz dependencies
    UI-001    Frontend builds + route-level tests for API base URLs, fields,
              error handling, auth expiry

Usage:
    python scripts/verify_rjsc_api.py /path/to/nlc_platform_clean
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
    for sub in ("app", "tests"):
        d = repo_root / sub
        if d.exists():
            targets.extend(p for p in d.rglob("*.py"))
    return sorted(targets)


def collect_route_signatures(repo_root: Path) -> list[dict]:
    """Return list of {file, function, method, path, line, decorator_text, signature_text}."""
    api_dir = repo_root / "app" / "api"
    routes = []
    if not api_dir.exists():
        return routes
    for py in api_dir.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(py))
        except SyntaxError:
            continue
        lines = text.splitlines()
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                attr = dec.func.attr
                if attr not in {"get", "post", "put", "patch", "delete"}:
                    continue
                path = "/"
                if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                    path = dec.args[0].value
                try:
                    dec_text = ast.unparse(dec)
                    sig_text = ast.unparse(node.args)
                except Exception:
                    dec_text = sig_text = ""
                routes.append({
                    "file": str(py), "function": node.name, "method": attr.upper(),
                    "path": path, "line": node.lineno,
                    "decorator_text": dec_text, "signature_text": sig_text,
                })
    return routes


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_rjsc_001(routes: list[dict], findings: list[Finding]) -> None:
    """RJSC-001: mark-filed operations need explicit company-level authorization."""
    filed_re = re.compile(r"/(?:.*filed|.*mark-filed|.*file-it|file_it)", re.I)
    filed_routes = [r for r in routes if filed_re.search(r["path"]) or "filed" in r["function"].lower()]
    for r in filed_routes:
        dec = r["decorator_text"] or ""
        sig = r["signature_text"] or ""
        if not any(k in dec or k in sig for k in
                   ("require_company_access", "require_tenant_access", "verify_company_access")):
            findings.append(Finding(
                "RJSC-001", r["file"], r["line"], "FAIL",
                f"Filing operation {r['method']} {r['path']} ({r['function']}) lacks "
                f"require_company_access dependency. Any authenticated user can mark a foreign "
                f"company's filing as filed.",
                "Add `current_company=Depends(require_company_access)` to the decorator chain.",
            ))


def check_rjsc_002(repo_root: Path, findings: list[Finding]) -> None:
    """RJSC-002: frontend/backend endpoint name conventions (underscore vs hyphen)."""
    frontend_dir = repo_root / "frontend" / "src"
    api_dir = repo_root / "app" / "api"
    if not (frontend_dir.exists() and api_dir.exists()):
        findings.append(Finding(
            "RJSC-002", "(repo)", 0, "INFO",
            "Frontend or API directory not found at expected location; cannot check naming parity.",
        ))
        return
    # Collect backend paths
    backend_paths = set()
    for py in api_dir.rglob("*.py"):
        try:
            text = py.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(py))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                    continue
                if dec.func.attr not in {"get", "post", "put", "patch", "delete"}:
                    continue
                if dec.args and isinstance(dec.args[0], ast.Constant) and isinstance(dec.args[0].value, str):
                    backend_paths.add(dec.args[0].value)
    # Collect frontend URL strings
    frontend_paths = set()
    for tsx in frontend_dir.rglob("*.ts*"):
        try:
            text = tsx.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'["\'](/api/v\d+/[^"\'\s]+)["\']', text):
            frontend_paths.add(m.group(1))
    # Check underscore-vs-hyphen mismatches
    mismatches = []
    for fp in frontend_paths:
        # try both hyphen->underscore and underscore->hyphen variants
        variants = {fp, fp.replace("-", "_"), fp.replace("_", "-")}
        if not variants & backend_paths:
            mismatches.append((fp, sorted(variants - {fp})))
    if mismatches:
        findings.append(Finding(
            "RJSC-002", "(frontend)", 0, "WARN",
            f"{len(mismatches)} frontend API URL(s) have no exact match in backend. "
            f"Possible underscore/hyphen mismatches. First 3: {mismatches[:3]}",
            "Standardize on hyphens for URLs (REST convention). Update either frontend URLs "
            "or backend route paths so they match character-for-character.",
        ))


def check_rjsc_003(repo_root: Path, findings: list[Finding]) -> None:
    """RJSC-003: frontend response shape vs backend schema."""
    frontend_dir = repo_root / "frontend" / "src"
    if not frontend_dir.exists():
        return
    # Look for response field references in frontend
    field_refs: dict[str, set[str]] = defaultdict(set)
    for tsx in frontend_dir.rglob("*.ts*"):
        try:
            text = tsx.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'\bdata\.(\w+)|\.(\w+)\s*=\s*data\.', text):
            field = m.group(1) or m.group(2)
            if field and not field.startswith("_"):
                field_refs[str(tsx)].add(field)
    # Backend schemas
    schema_dir = repo_root / "app" / "schemas"
    backend_fields: set[str] = set()
    if schema_dir.exists():
        for py in schema_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8", errors="ignore")
                tree = ast.parse(text)
            except (SyntaxError, OSError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                    backend_fields.add(node.target.id)
                if isinstance(node, ast.ClassDef):
                    for stmt in node.body:
                        if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                            backend_fields.add(stmt.target.id)
    if not backend_fields or not field_refs:
        return
    # Look for fields used in frontend but missing in backend
    frontend_only: set[str] = set()
    for _, fields in field_refs.items():
        frontend_only |= fields - backend_fields
    # Filter out common JS/TS noise
    frontend_only = {f for f in frontend_only if not f.startswith(("map", "filter", "reduce", "length", "toString", "indexOf", "slice", "splice"))}
    if frontend_only:
        findings.append(Finding(
            "RJSC-003", "(frontend)", 0, "WARN",
            f"Frontend references {len(frontend_only)} field(s) not found in backend schemas. "
            f"Sample: {sorted(frontend_only)[:10]}",
            "Either add the missing field to the backend Pydantic schema or fix the frontend "
            "to use the correct field name.",
        ))


def check_rjsc_004(routes: list[dict], repo_root: Path, findings: list[Finding]) -> None:
    """RJSC-004: cross-tenant tests for each RJSC route."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    rjsc_routes = [r for r in routes if "rjsc" in r["file"].lower() or "rjsc" in r["path"].lower()]
    if not rjsc_routes:
        return
    cross_tenant_test_count = 0
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"cross[_-]?tenant|other_company|company_id.*other", text, re.I):
            cross_tenant_test_count += 1
    if cross_tenant_test_count < len(rjsc_routes):
        findings.append(Finding(
            "RJSC-004", "(tests)", 0, "FAIL",
            f"Found {len(rjsc_routes)} RJSC routes but only {cross_tenant_test_count} cross-tenant "
            f"test file(s). Most routes have NO cross-tenant coverage.",
            "Add a cross-tenant test per RJSC route: authenticate as user A, call route with "
            "company_id of company B, assert 403/404.",
        ))


def check_rjsc_005(repo_root: Path, findings: list[Finding]) -> None:
    """RJSC-005: filing lifecycle transitions must reject invalid transitions."""
    filing_files = [
        repo_root / "app" / "models" / "filings.py",
        repo_root / "app" / "services" / "filing_service.py",
        repo_root / "app" / "api" / "filings.py",
    ]
    found_transition_check = False
    for p in filing_files:
        if not p.exists():
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Look for allowed_transitions / valid_transitions / state machine
        if re.search(r"allowed_transitions|valid_transitions|VALID_TRANSITIONS|transition_check", text, re.I):
            found_transition_check = True
    if not found_transition_check:
        findings.append(Finding(
            "RJSC-005", "(filings)", 0, "FAIL",
            "No visible filing-state transition validation. Invalid transitions (e.g. FILED -> "
            "PENDING) may silently succeed.",
            "Add a `VALID_TRANSITIONS` dict mapping current_status -> set of allowed next statuses; "
            "every PATCH handler must validate against this map.",
        ))


def check_rjsc_006(repo_root: Path, findings: list[Finding]) -> None:
    """RJSC-006: filing deadlines/dates need consistent timezone semantics."""
    py_files = collect_py_files(repo_root)
    suspicious = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # dateutil, datetime.now() without tz, datetime.utcnow()
        for m in re.finditer(r"datetime\.now\(\)|datetime\.utcnow\(\)", text):
            ctx_before = text[max(0, m.start() - 100):m.start()]
            ctx_after = text[m.end():m.end() + 100]
            ctx = (ctx_before + ctx_after).lower()
            if "filing" in ctx or "deadline" in ctx or "agm" in ctx or "annual_return" in ctx:
                # check if tz-aware version is used elsewhere in the file
                if "datetime.now(tz" not in text and "datetime.now(timezone" not in text and "aware" not in text.lower():
                    lineno = text[:m.start()].count("\n") + 1
                    suspicious.append((p, lineno, m.group(0)))
    for p, ln, snippet in suspicious[:10]:
        findings.append(Finding(
            "RJSC-006", str(p), ln, "WARN",
            f"Filing/deadline code uses naive `{snippet}`. Without timezone, the same instant "
            f"in different deployment regions yields different dates.",
            "Use `datetime.now(timezone.utc)` (Python 3.11+) or `datetime.utcnow().replace(tzinfo=timezone.utc)`. "
            "Store all deadline timestamps as UTC; convert to Asia/Dhaka only at display.",
        ))


def check_api_001(repo_root: Path, findings: list[Finding]) -> None:
    """API-001: live API rule parity check returns 401."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    parity_tests = []
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"rule.*parity|parity.*rule|live.*parity|/api/v\d+/rules/parity", text, re.I):
            parity_tests.append(p)
    if not parity_tests:
        findings.append(Finding(
            "API-001", "(tests)", 0, "FAIL",
            "No parity test found at all. Cannot verify whether the API serves the same rule "
            "corpus as the engine seed.",
            "Add tests/integration/test_api_rule_parity.py: authenticate properly (use a fixture "
            "token), GET /api/v1/rules, then compare returned rule IDs to STATUTORY_RULE_REGISTRY.",
        ))
        return
    # Look for 401 / Unauthorised assertions
    suspicious = []
    for p in parity_tests:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "401" in text or "unauthor" in text.lower() or "xfail" in text.lower() or "skip" in text.lower():
            suspicious.append(p)
    if suspicious:
        findings.append(Finding(
            "API-001", str(suspicious[0]), 0, "FAIL",
            f"Parity test in {suspicious[0].name} contains 401/skip/xfail markers -- likely the "
            f"test is failing or being skipped due to auth. Live parity NOT actually verified.",
            "Fix the test fixtures so the parity check returns 200 with the full rule corpus. "
            "Do NOT skip -- this is a critical correctness check.",
        ))


def check_api_002(routes: list[dict], findings: list[Finding]) -> None:
    """API-002: every router must have explicit auth/authz dependencies."""
    auth_dep_re = re.compile(r"get_current_user|require_roles|require_company_access|require_tenant_access|require_superadmin")
    files_missing = defaultdict(int)
    files_total = defaultdict(int)
    for r in routes:
        files_total[r["file"]] += 1
        dec = r["decorator_text"] or ""
        sig = r["signature_text"] or ""
        if not auth_dep_re.search(dec) and not auth_dep_re.search(sig):
            files_missing[r["file"]] += 1
    for file, miss in sorted(files_missing.items(), key=lambda kv: -kv[1]):
        total = files_total[file]
        if miss > 0:
            sev = "FAIL" if miss / total > 0.5 else "WARN"
            findings.append(Finding(
                "API-002", file, 0, sev,
                f"{miss}/{total} routes in {file} lack any auth/authz dependency.",
                "Add `current_user=Depends(get_current_user)` to every route that should be "
                "authenticated. Add a role guard for state-changing operations.",
            ))


def check_ui_001(repo_root: Path, findings: list[Finding]) -> None:
    """UI-001: frontend builds + route-level tests for API base URLs, fields, errors, auth expiry."""
    frontend_dir = repo_root / "frontend"
    if not frontend_dir.exists():
        return
    # check API_BASE declaration
    api_base_count = 0
    for tsx in frontend_dir.rglob("*.ts*"):
        try:
            text = tsx.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        api_base_count += len(re.findall(r'\bAPI_BASE\s*[:=]', text))
    if api_base_count > 1:
        findings.append(Finding(
            "UI-001", "(frontend)", 0, "WARN",
            f"{api_base_count} API_BASE declarations across frontend. Likely a duplicate-"
            f"declaration conflict (previously reported).",
            "Consolidate into a single env-aware API_BASE in a shared config module "
            "(e.g. lib/config.ts) and import everywhere.",
        ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/rjsc_api_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC RJSC / API / UI Audit ===")
    print(f"Repo: {repo_root}")
    print()

    routes = collect_route_signatures(repo_root)
    print(f"Discovered {len(routes)} routes across {len(set(r['file'] for r in routes))} files.")
    print()

    findings: list[Finding] = []
    check_rjsc_001(routes, findings)
    check_rjsc_002(repo_root, findings)
    check_rjsc_003(repo_root, findings)
    check_rjsc_004(routes, repo_root, findings)
    check_rjsc_005(repo_root, findings)
    check_rjsc_006(repo_root, findings)
    check_api_001(repo_root, findings)
    check_api_002(routes, findings)
    check_ui_001(repo_root, findings)

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
        "route_count": len(routes),
        "findings": [asdict(f) for f in findings],
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"JSON report: {args.output}")

    fail_total = sum(1 for f in findings if f.severity == "FAIL")
    return 0 if fail_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())