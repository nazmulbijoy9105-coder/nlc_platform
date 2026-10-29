#!/usr/bin/env python3
"""
SEC-003 through SEC-012 -- Tenant isolation, auth & admin endpoint audit.

Static analyzer that scans the NLC platform source tree (app/api/*.py) and
reports findings for each SEC check WITHOUT requiring a live server. The
output flags gaps that must be fixed or verified at runtime against a real
deployed instance.

Usage:
    python scripts/verify_tenant_isolation.py /path/to/nlc_platform_clean
    python scripts/verify_tenant_isolation.py /path/to/repo --output /tmp/sec.json

Findings produced (one row per gap, may be many per check ID):
    SEC-003   Endpoints touching company_id without require_company_access
    SEC-004   State-changing routes (POST/PATCH/DELETE) without role guard
    SEC-005   Staff/admin exception sites lacking explicit audit log
    SEC-006   JWT helpers - check for revocation list, expiry, refresh rotation
    SEC-007   TOTP secret storage - check encryption-at-rest usage
    SEC-008   Admin routers - verify every route has a role dep
    SEC-009   Background endpoints - fail-closed when auth missing
    SEC-010   SQL string interpolation in admin queries
    SEC-011   Super-admin bootstrap & account recovery - privileged path audit
    SEC-012   Cross-tenant test coverage - count of integration tests touching
              a foreign company_id

This script is intentionally conservative: it prefers to emit a WARN and let
a human review rather than declare PASS on something it cannot fully verify.
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
import os
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class Finding:
    check_id: str
    file: str
    line: int
    severity: str  # FAIL | WARN | INFO
    detail: str
    suggested_fix: str = ""


# ---------------------------------------------------------------------------
# AST walker
# ---------------------------------------------------------------------------

class RouterVisitor(ast.NodeVisitor):
    """Walks a FastAPI router file and collects route decorators + signatures."""

    STATE_CHANGING_METHODS = {"post", "put", "patch", "delete"}

    def __init__(self, file_path: str, lines: list[str]):
        self.file_path = file_path
        self.lines = lines
        self.findings: list[Finding] = []
        # route decorator signatures we encounter, for downstream checks
        self.routes: list[dict[str, Any]] = []

    def _line_text(self, lineno: int) -> str:
        if 0 <= lineno - 1 < len(self.lines):
            return self.lines[lineno - 1].strip()
        return ""

    def _is_router_decorator(self, dec: ast.expr) -> tuple[str, str] | None:
        """Return (http_method, route_path) if decorator is @router.<method>(...)."""
        if not isinstance(dec, ast.Call):
            return None
        if not isinstance(dec.func, ast.Attribute):
            return None
        attr = dec.func.attr  # get, post, patch, etc.
        if attr not in {"get", "post", "put", "patch", "delete"}:
            return None
        # First positional arg is path (string). May be missing (defaults to "/").
        path = "/"
        if dec.args:
            arg0 = dec.args[0]
            if isinstance(arg0, ast.Constant) and isinstance(arg0.value, str):
                path = arg0.value
        return attr, path

    def _decorator_depends_text(self, dec: ast.expr) -> str:
        """Return a stringified snapshot of any Depends(...) inside a decorator."""
        try:
            return ast.unparse(dec) if hasattr(ast, "unparse") else ""
        except Exception:
            return ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # collect router decorators
        route_decs = []
        for dec in node.decorator_list:
            info = self._is_router_decorator(dec)
            if info is not None:
                route_decs.append((info, dec))
        if not route_decs:
            # still walk for nested defs
            self.generic_visit(node)
            return

        for (method, path), dec_node in route_decs:
            dec_text = self._decorator_depends_text(dec_node)
            sig_text = ast.unparse(node.args) if hasattr(ast, "unparse") else ""
            body_text = "\n".join(self.lines[node.lineno - 1: node.end_lineno or node.lineno])
            self.routes.append({
                "function": node.name,
                "method": method.upper(),
                "path": path,
                "line": node.lineno,
                "decorator_text": dec_text,
                "signature_text": sig_text,
                "body_text": body_text,
            })

        self.generic_visit(node)
    visit_AsyncFunctionDef = visit_FunctionDef  # Phase 6a: catch async def routes


# ---------------------------------------------------------------------------
# Individual SEC checks
# ---------------------------------------------------------------------------

COMPANY_PATH_RE = re.compile(r"\{company_id\}|\{companyId\}|company_id\b")
NESTED_RESOURCE_RE = re.compile(
    r"/(?:companies|company)/(?:[^/]+)/(?:"
    r"documents|filings|agm|audit|annual-returns|annual_returns|statutory-registers|statutory_registers|"
    r"transfers|resolutions|flags|scores|rescue|engagement|calendar|notifications|webhooks|invoices|payments)"
)


def check_sec_003(routes_by_file: dict[str, list[dict]], findings: list[Finding]) -> None:
    """SEC-003: company-scoped routes must have require_company_access dependency."""
    for file, routes in routes_by_file.items():
        for r in routes:
            path = r["path"]
            if not COMPANY_PATH_RE.search(path) and "company_id" not in (r["signature_text"] or ""):
                continue
            dec_text = r["decorator_text"] or ""
            sig_text = r["signature_text"] or ""
            has_access_guard = (
                "require_company_access" in dec_text
                or "require_company_access" in sig_text
                or "require_tenant_access" in dec_text
                or "require_tenant_access" in sig_text
                or "verify_company_access" in dec_text
                or "verify_company_access" in sig_text
            )
            if not has_access_guard:
                findings.append(Finding(
                    check_id="SEC-003",
                    file=file,
                    line=r["line"],
                    severity="FAIL",
                    detail=(
                        f"{r['method']} {path} ({r['function']}) touches company-scoped "
                        f"data but decorator/signature contains no require_company_access / "
                        f"require_tenant_access dependency."
                    ),
                    suggested_fix=(
                        "Add `current_company=Depends(require_company_access)` (or equivalent) "
                        "to the decorator or function signature, AND verify the DB session sets "
                        "app.current_user_id so RLS filters cross-tenant queries to zero rows."
                    ),
                ))


def check_sec_004(routes_by_file: dict[str, list[dict]], findings: list[Finding]) -> None:
    """SEC-004: state-changing routes must have a role guard."""
    ROLE_GUARD_RE = re.compile(r"require_roles|require_role|require_scopes|RoleChecker|require_permission")
    for file, routes in routes_by_file.items():
        for r in routes:
            if r["method"].lower() not in {"post", "put", "patch", "delete"}:
                continue
            dec_text = r["decorator_text"] or ""
            sig_text = r["signature_text"] or ""
            if not (ROLE_GUARD_RE.search(dec_text) or ROLE_GUARD_RE.search(sig_text)):
                # downgrade from FAIL to WARN if at least current_user is present
                if "get_current_user" in dec_text or "get_current_user" in sig_text:
                    findings.append(Finding(
                        check_id="SEC-004",
                        file=file,
                        line=r["line"],
                        severity="WARN",
                        detail=(
                            f"{r['method']} {r['path']} ({r['function']}) has current_user "
                            f"but no explicit role guard. Client-view users could mutate."
                        ),
                        suggested_fix=(
                            "Add `Depends(require_roles(['admin','staff','auditor']))` "
                            "(or equivalent) to the decorator."
                        ),
                    ))
                else:
                    findings.append(Finding(
                        check_id="SEC-004",
                        file=file,
                        line=r["line"],
                        severity="FAIL",
                        detail=(
                            f"{r['method']} {r['path']} ({r['function']}) is state-changing "
                            f"with no role dependency AND no current_user dep -- any authenticated "
                            f"caller could invoke it."
                        ),
                        suggested_fix=(
                            "Add both: `current_user=Depends(get_current_user)` AND a role guard "
                            "via `Depends(require_roles([...))`."
                        ),
                    ))


def check_sec_005(routes_by_file: dict[str, list[dict]], findings: list[Finding]) -> None:
    """SEC-005: staff/admin exception sites should write to an audit log."""
    for file, routes in routes_by_file.items():
        for r in routes:
            body = r["body_text"] or ""
            if not (any(k in body for k in ("is_staff", "is_admin", "is_superuser", "Role.ADMIN", "Role.STAFF"))):
                continue
            if not any(k in body for k in ("activity_log", "audit_log", "log_activity", "log_audit", "write_audit")):
                findings.append(Finding(
                    check_id="SEC-005",
                    file=file,
                    line=r["line"],
                    severity="WARN",
                    detail=(
                        f"{r['function']} references a staff/admin flag but the body contains "
                        f"no audit-log write call. Privileged access must be auditable."
                    ),
                    suggested_fix=(
                        "Call `await log_activity(db, current_user, action='...', "
                        "target_company_id=...)` in the privileged branch."
                    ),
                ))


def check_sec_006(repo_root: Path, findings: list[Finding]) -> None:
    """SEC-006: JWT helpers -- look for revocation, expiry, refresh rotation."""
    candidates = [
        repo_root / "app" / "core" / "security.py",
        repo_root / "app" / "core" / "auth.py",
        repo_root / "app" / "core" / "jwt.py",
        repo_root / "app" / "api" / "auth.py",
        repo_root / "app" / "services" / "auth_service.py",
    ]
    found = [p for p in candidates if p.exists()]
    if not found:
        findings.append(Finding(
            check_id="SEC-006", file="?", line=0, severity="WARN",
            detail="No JWT/auth helper module found at expected paths. "
                   "Cannot verify revocation / refresh rotation.",
        ))
        return
    for p in found:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "blacklist" not in text.lower() and "revoked" not in text.lower() and "jti" not in text.lower():
            findings.append(Finding(
                check_id="SEC-006", file=str(p), line=0, severity="WARN",
                detail="No JWT revocation mechanism (blacklist/jti/revoked_set) detected in auth helper.",
                suggested_fix="Maintain a revoked-token set keyed by jti; check on every request.",
            ))
        if "exp" not in text.lower():
            findings.append(Finding(
                check_id="SEC-006", file=str(p), line=0, severity="FAIL",
                detail="JWT helper does not appear to set/check `exp` claim. Tokens may never expire.",
            ))
        # refresh rotation: a /refresh endpoint that issues a new refresh token AND revokes the old
        if "refresh" in text.lower() and "rotate" not in text.lower() and "revoke" not in text.lower():
            findings.append(Finding(
                check_id="SEC-006", file=str(p), line=0, severity="WARN",
                detail="Refresh token flow detected but no rotate/revoke logic -- refresh token replay risk.",
            ))


def check_sec_007(repo_root: Path, findings: list[Finding]) -> None:
    """SEC-007: TOTP secrets must be encrypted at rest."""
    candidates = [
        repo_root / "app" / "models" / "user.py",
        repo_root / "app" / "models" / "auth.py",
        repo_root / "app" / "services" / "mfa_service.py",
        repo_root / "app" / "services" / "totp_service.py",
        repo_root / "app" / "core" / "security.py",
    ]
    for p in candidates:
        if not p.exists():
            continue
        text = p.read_text(encoding="utf-8", errors="ignore")
        # Look for a TOTP/OTP secret column or attribute
        if "totp_secret" in text.lower() or "otp_secret" in text.lower() or "mfa_secret" in text.lower():
            if "fernet" not in text.lower() and "encrypt" not in text.lower() and "ciphertext" not in text.lower():
                findings.append(Finding(
                    check_id="SEC-007", file=str(p), line=0, severity="FAIL",
                    detail="TOTP secret stored without visible encryption-at-rest (no Fernet / encrypt() call near the field).",
                    suggested_fix="Encrypt TOTP secret with a key from env (e.g. Fernet) before persisting.",
                ))


def check_sec_008(routes_by_file: dict[str, list[dict]], findings: list[Finding]) -> None:
    """SEC-008: admin routers -- every route must have a role dep."""
    ADMIN_FILE_RE = re.compile(r"admin|superuser|backoffice|ops", re.I)
    for file, routes in routes_by_file.items():
        if not ADMIN_FILE_RE.search(os.path.basename(file)):
            continue
        for r in routes:
            dec_text = r["decorator_text"] or ""
            sig_text = r["signature_text"] or ""
            if not any(k in dec_text or k in sig_text for k in
                       ("require_roles", "require_role", "RoleChecker", "require_superadmin")):
                findings.append(Finding(
                    check_id="SEC-008", file=file, line=r["line"], severity="FAIL",
                    detail=(
                        f"Admin router {file}::{r['function']} ({r['method']} {r['path']}) "
                        f"has no role dependency -- any authenticated user can hit it."
                    ),
                    suggested_fix="Add `Depends(require_roles(['superadmin']))` or similar.",
                ))


def check_sec_009(repo_root: Path, findings: list[Finding]) -> None:
    """SEC-009: background evaluation endpoints fail closed when auth missing."""
    bg_dirs = [repo_root / "app" / "worker", repo_root / "app" / "api" / "worker.py",
               repo_root / "app" / "api" / "admin.py"]
    bg_files = []
    for d in bg_dirs:
        if d.exists() and d.is_file():
            bg_files.append(d)
        elif d.exists() and d.is_dir():
            bg_files.extend(d.rglob("*.py"))
    if not bg_files:
        findings.append(Finding(
            check_id="SEC-009", file="?", line=0, severity="INFO",
            detail="No worker API module found -- skipping background endpoint check.",
        ))
        return
    for f in bg_files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        # Look for missing-secret / missing-auth branches
        if "evaluate" in text.lower() or "trigger_evaluation" in text.lower():
            if "raise" not in text and "HTTPException" not in text:
                findings.append(Finding(
                    check_id="SEC-009", file=str(f), line=0, severity="WARN",
                    detail="Background evaluation endpoint lacks explicit fail-closed (no raise/HTTPException found).",
                ))


def check_sec_010(repo_root: Path, findings: list[Finding]) -> None:
    """SEC-010: SQL string interpolation in admin queries."""
    SUSPICIOUS_SQL = re.compile(
        r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE).*\{[^}]+\}.*["\']',
        re.IGNORECASE | re.DOTALL,
    )
    SUSPICIOUS_SQL2 = re.compile(
        r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM|WHERE).*["\'].*%.*',
        re.IGNORECASE,
    )
    py_files = list((repo_root / "app").rglob("*.py")) if (repo_root / "app").exists() else []
    for f in py_files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in SUSPICIOUS_SQL.finditer(text):
            lineno = text[:m.start()].count("\n") + 1
            findings.append(Finding(
                check_id="SEC-010", file=str(f), line=lineno, severity="FAIL",
                detail=f"Possible f-string SQL interpolation: {m.group(0)[:120]}",
                suggested_fix="Use parameterized queries: cur.execute('SELECT ... WHERE id = %s', (id,))",
            ))
        for m in SUSPICIOUS_SQL2.finditer(text):
            lineno = text[:m.start()].count("\n") + 1
            # only flag if it looks like a real SQL string, not a format string
            if "%s" in m.group(0) or "%(" in m.group(0):
                continue  # parameterized form
            findings.append(Finding(
                check_id="SEC-010", file=str(f), line=lineno, severity="WARN",
                detail=f"Possible %-formatted SQL string: {m.group(0)[:120]}",
            ))


def check_sec_011(repo_root: Path, findings: list[Finding]) -> None:
    """SEC-011: super-admin bootstrap & account recovery paths."""
    candidates = [
        repo_root / "app" / "api" / "auth.py",
        repo_root / "app" / "api" / "admin.py",
        repo_root / "app" / "api" / "users.py",
        repo_root / "app" / "scripts" / "create_superuser.py",
        repo_root / "scripts" / "create_superuser.py",
        repo_root / "app" / "services" / "auth_service.py",
        repo_root / "app" / "services" / "user_service.py",
    ]
    found = [p for p in candidates if p.exists()]
    if not found:
        findings.append(Finding(
            check_id="SEC-011", file="?", line=0, severity="INFO",
            detail="No bootstrap/recovery module found at expected paths -- skipping SEC-011.",
        ))
        return
    for p in found:
        text = p.read_text(encoding="utf-8", errors="ignore")
        if "superuser" in text.lower() or "is_superuser" in text.lower() or "super_admin" in text.lower():
            # check for env-var based bootstrapping that requires affirmative flag
            if "getenv" in text.lower() and "bool" in text.lower():
                continue  # looks gated by env var
            if "init_admin" in text.lower() or "create_superuser" in text.lower():
                if "if not" not in text.lower():
                    findings.append(Finding(
                        check_id="SEC-011", file=str(p), line=0, severity="WARN",
                        detail="Super-user bootstrap code found but no visible guard (e.g. `if not os.getenv(...)`).",
                    ))


def check_sec_012(repo_root: Path, findings: list[Finding]) -> None:
    """SEC-012: count of cross-tenant integration tests touching a foreign company_id."""
    test_dirs = [repo_root / "tests" / "integration", repo_root / "tests" / "e2e"]
    test_files = []
    for d in test_dirs:
        if d.exists():
            test_files.extend(d.rglob("*.py"))
    cross_tenant_tests = 0
    for tf in test_files:
        try:
            text = tf.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # Look for tests that explicitly swap company_id / tenant
        if re.search(r"company_id.*=.*other|tenant.*=.*other|cross[_-]?tenant|other_company", text, re.I):
            cross_tenant_tests += 1
    if cross_tenant_tests == 0:
        findings.append(Finding(
            check_id="SEC-012", file="(tests/integration)", line=0, severity="FAIL",
            detail="No cross-tenant integration tests detected by heuristic search.",
            suggested_fix="Add at least one test per RJSC/filings/rescue/documents route that "
                          "calls the route with another tenant's company_id and asserts 404/403.",
        ))
    else:
        findings.append(Finding(
            check_id="SEC-012", file="(tests/integration)", line=0, severity="INFO",
            detail=f"Found {cross_tenant_tests} file(s) with cross-tenant heuristic match -- review each for real assertion.",
        ))


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def scan_repo(repo_root: Path) -> list[Finding]:
    api_dir = repo_root / "app" / "api"
    if not api_dir.exists():
        return [Finding(
            check_id="ALL", file="?", line=0, severity="FAIL",
            detail=f"No app/api directory at {repo_root}. Is this the right repo?",
        )]
    routes_by_file: dict[str, list[dict]] = {}
    for py_file in sorted(api_dir.rglob("*.py")):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(py_file))
        except SyntaxError as exc:
            continue
        visitor = RouterVisitor(str(py_file), text.splitlines())
        visitor.visit(tree)
        if visitor.routes:
            routes_by_file[str(py_file)] = visitor.routes

    findings: list[Finding] = []
    check_sec_003(routes_by_file, findings)
    check_sec_004(routes_by_file, findings)
    check_sec_005(routes_by_file, findings)
    check_sec_006(repo_root, findings)
    check_sec_007(repo_root, findings)
    check_sec_008(routes_by_file, findings)
    check_sec_009(repo_root, findings)
    check_sec_010(repo_root, findings)
    check_sec_011(repo_root, findings)
    check_sec_012(repo_root, findings)
    return findings


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/sec_report.json",
                   help="Where to write JSON report.")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC Tenant Isolation Audit ===")
    print(f"Repo: {repo_root}")
    print()

    findings = scan_repo(repo_root)

    by_check: dict[str, list[Finding]] = {}
    for f in findings:
        by_check.setdefault(f.check_id, []).append(f)

    print(f"=== SUMMARY ===")
    for cid in sorted(by_check):
        rows = by_check[cid]
        fail = sum(1 for r in rows if r.severity == "FAIL")
        warn = sum(1 for r in rows if r.severity == "WARN")
        info = sum(1 for r in rows if r.severity == "INFO")
        print(f"  {cid}: FAIL={fail} WARN={warn} INFO={info}  (total={len(rows)})")
    print()

    for cid in sorted(by_check):
        print(f"--- {cid} ---")
        for r in by_check[cid]:
            marker = {"FAIL": "XX", "WARN": "!!", "INFO": "--"}.get(r.severity, "??")
            print(f"[{marker}] {r.file}:{r.line}  {r.detail}")
            if r.suggested_fix:
                print(f"      -> FIX: {r.suggested_fix}")
        print()

    report = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "repo": str(repo_root),
        "findings": [asdict(f) for f in findings],
        "summary": {cid: len(rows) for cid, rows in by_check.items()},
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(json.dumps(report, indent=2))
    print(f"JSON report: {args.output}")

    fail_total = sum(1 for f in findings if f.severity == "FAIL")
    return 0 if fail_total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())