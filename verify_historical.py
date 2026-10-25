#!/usr/bin/env python3
"""
Section M -- Historical issues audit.

Re-verifies items reported in prior NLC reviews against the current source:

    HIST-LBR-001/002/003   LBR-* rule behaviour
    HIST-DUPKEYS            Duplicate dictionary keys
    HIST-OR-TRUE            Suspicious `or True` assertions in tests
    HIST-VULNDEPS           Vulnerable dependency versions
    HIST-DUP-API-BASE       Frontend duplicate API_BASE declaration
    HIST-MIG-DRIFT          Migration/schema drift + DB permissions
    HIST-WORKER-MODULE      Worker module availability + scheduled-task impl
    HIST-RESCUE-CONTRACT    Rescue engagement contract & lifecycle inconsistencies

Usage:
    python scripts/verify_historical.py /path/to/nlc_platform_clean
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
from collections import defaultdict, Counter
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


def check_lbr_rules(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-LBR-001/002/003: LBR-* rule behaviour."""
    py_files = collect_py_files(repo_root)
    lbr_files = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r'\bLBR-001\b|\bLBR-002\b|\bLBR-003\b', text):
            lbr_files.append(p)
    if not lbr_files:
        findings.append(Finding(
            "HIST-LBR", "?", 0, "INFO",
            "No LBR-* rule references detected. May not apply.",
        ))
        return
    # Check that LBR rules fire only for labour-law applicability
    for p in lbr_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for rule_id in ("LBR-001", "LBR-002", "LBR-003"):
            if rule_id not in text:
                continue
            # Find the rule context
            for m in re.finditer(rf'{rule_id}[^a-z]', text):
                lineno = text[:m.start()].count("\n") + 1
                ctx = text[max(0, m.start() - 200):m.end() + 400]
                # Look for labour-law applicability gate
                if not re.search(r"labour|labor|workforce|employee_count|factory", ctx, re.I):
                    findings.append(Finding(
                        f"HIST-{rule_id}", str(p), lineno, "WARN",
                        f"{rule_id} fires without visible labour-law applicability gate. "
                        f"Companies without employees shouldn't trigger LBR rules.",
                        "Add an applicability predicate: only fire LBR-* when company has 7+ "
                        "employees (Labour Act 2006 threshold).",
                    ))


def check_dupkeys(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-DUPKEYS: duplicate dictionary keys."""
    py_files = collect_py_files(repo_root)
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(text, filename=str(p))
        except (SyntaxError, OSError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Dict):
                continue
            keys = []
            for k in node.keys:
                if isinstance(k, ast.Constant):
                    keys.append(k.value)
                elif isinstance(k, ast.Name):
                    keys.append(k.id)
            dupes = [k for k, c in Counter(keys).items() if c > 1]
            if dupes:
                findings.append(Finding(
                    "HIST-DUPKEYS", str(p), node.lineno, "FAIL",
                    f"Duplicate dict keys at line {node.lineno}: {dupes}. Last write wins -- "
                    f"earlier value silently dropped.",
                    "Rename or remove the duplicate. If intentional, add a comment.",
                ))


def check_or_true(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-OR-TRUE: suspicious `or True` in tests / assertions."""
    py_files = list((repo_root / "tests").rglob("*.py")) if (repo_root / "tests").exists() else []
    if not py_files:
        return
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r"\bor\s+True\b", text):
            lineno = text[:m.start()].count("\n") + 1
            line = text.splitlines()[lineno - 1]
            findings.append(Finding(
                "HIST-OR-TRUE", str(p), lineno, "WARN",
                f"`or True` makes the assertion always pass: {line.strip()}",
                "Remove the `or True`. If genuinely intended for skip-on-error, use "
                "pytest.skip() instead.",
            ))


def check_vulndeps(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-VULNDEPS: vulnerable dependency versions."""
    deps_files = []
    for pat in ("requirements.txt", "requirements-dev.txt", "pyproject.toml",
                "Pipfile", "Pipfile.lock", "poetry.lock"):
        p = repo_root / pat
        if p.exists():
            deps_files.append(p)
    # Known vulnerable pins (from previous scans)
    KNOWN_BAD = {
        "pyyaml<5.4": "CVE-2020-14343",
        "jinja2<2.11.3": "CVE-2020-28493",
        "pillow<8.0": "multiple CVEs",
        "cryptography<3.4": "CVE-2020-36196",
        "sqlalchemy<1.3.0": "CVE-2019-7164",
        "starlette<0.36": "CVE-2023-29159",
        "fastapi<0.65": "multiple CVEs",
        "uvicorn<0.11": "CVE-2020-15168",
    }
    for p in deps_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        text_lower = text.lower()
        for pkg, cve in KNOWN_BAD.items():
            base = pkg.split("<")[0]
            if base in text_lower:
                # check version
                m = re.search(rf'{base}[^a-z0-9]*([<>=!~]+\s*[\d.]+)', text, re.I)
                if m:
                    version_spec = m.group(1)
                    # crude check
                    if "<" in version_spec:
                        try:
                            ver_num = re.search(r"[\d.]+", version_spec).group(0)
                            major = int(ver_num.split(".")[0])
                            required_major = int(pkg.split("<")[1].split(".")[0])
                            if major < required_major:
                                findings.append(Finding(
                                    "HIST-VULNDEPS", str(p), 0, "WARN",
                                    f"{base} pin {version_spec} may include {cve}.",
                                    f"Upgrade to {pkg} or newer.",
                                ))
                        except Exception:
                            pass


def check_dup_api_base(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-DUP-API-BASE: frontend duplicate API_BASE declaration."""
    frontend_dir = repo_root / "frontend"
    if not frontend_dir.exists():
        return
    api_base_locations = []
    for tsx in frontend_dir.rglob("*.ts*"):
        try:
            text = tsx.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in re.finditer(r'\bAPI_BASE\s*[:=]\s*[\'"]?[^\'";\s]+', text):
            lineno = text[:m.start()].count("\n") + 1
            api_base_locations.append((tsx, lineno, m.group(0)[:80]))
    if len(api_base_locations) > 1:
        for loc in api_base_locations[:5]:
            findings.append(Finding(
                "HIST-DUP-API-BASE", str(loc[0]), loc[1], "WARN",
                f"Duplicate API_BASE declaration: `{loc[2]}`",
                "Move API_BASE to a shared lib/config.ts; import everywhere.",
            ))


def check_mig_drift(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-MIG-DRIFT: migration/schema drift + DB permissions."""
    # Already covered by DB-001 check; here we look for ownership-related code
    alembic_dir = repo_root / "alembic"
    if not alembic_dir.exists():
        return
    env_file = alembic_dir / "env.py"
    if not env_file.exists():
        return
    try:
        text = env_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    if "owner" in text.lower() or "REVOKE" in text or "GRANT" in text:
        findings.append(Finding(
            "HIST-MIG-DRIFT", str(env_file), 0, "INFO",
            "alembic/env.py mentions owner/GRANT/REVOKE -- verify deployed DB grants match.",
        ))
    # Check if there's a migration that mentions RLS
    rls_migrations = []
    for p in (alembic_dir / "versions").rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "ENABLE ROW LEVEL SECURITY" in text.upper() or "CREATE POLICY" in text.upper():
            rls_migrations.append(p)
    if rls_migrations:
        findings.append(Finding(
            "HIST-MIG-DRIFT", str(rls_migrations[0]), 0, "INFO",
            f"{len(rls_migrations)} migration(s) contain RLS statements. VERIFY these were "
            f"actually applied on the deployed DB (run verify_rls.py).",
        ))
    else:
        findings.append(Finding(
            "HIST-MIG-DRIFT", "(migrations)", 0, "FAIL",
            "No migration found that creates RLS policies. Tenant isolation depends entirely "
            "on RLS -- none exists in repo history.",
            "Add an alembic migration that: (a) creates a tenant role, (b) enables RLS on every "
            "company-scoped table, (c) creates USING/WITH CHECK policies referencing "
            "app.current_user_id.",
        ))


def check_worker_module(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-WORKER-MODULE: worker module availability + scheduled-task impl."""
    worker_dir = repo_root / "app" / "worker"
    if not worker_dir.exists():
        findings.append(Finding(
            "HIST-WORKER-MODULE", "?", 0, "WARN",
            "No app/worker directory. Background evaluation not implemented.",
        ))
        return
    # Check for tasks/__init__.py and registered tasks
    init_file = worker_dir / "tasks" / "__init__.py"
    if not init_file.exists():
        findings.append(Finding(
            "HIST-WORKER-MODULE", str(worker_dir), 0, "WARN",
            "No app/worker/tasks/__init__.py. Tasks may not be importable / registered.",
        ))
        return
    try:
        text = init_file.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return
    if not re.search(r"celery_app\.autodiscover|include\s*=|import_module", text, re.I):
        findings.append(Finding(
            "HIST-WORKER-MODULE", str(init_file), 0, "WARN",
            "Worker tasks module does not autodiscover or include task modules. Tasks may be "
            "defined but never registered.",
            "Add `celery_app.autodiscover_tasks(['app.worker.tasks'])` or explicit `include=[...]`.",
        ))


def check_rescue_contract(repo_root: Path, findings: list[Finding]) -> None:
    """HIST-RESCUE-CONTRACT: rescue engagement contract & lifecycle inconsistencies."""
    test_dir = repo_root / "tests"
    if test_dir.exists():
        contract_test_count = 0
        for p in test_dir.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if re.search(r"def\s+test_.*rescue.*contract|def\s+test_.*engagement.*contract", text, re.I):
                contract_test_count += 1
        if contract_test_count == 0:
            findings.append(Finding(
                "HIST-RESCUE-CONTRACT", "(tests)", 0, "WARN",
                "No rescue engagement contract test found.",
                "Add tests/unit/test_rescue_engagement_contract.py with explicit contract "
                "assertions: caller args, return shape, DB side-effects, audit row.",
            ))
    # Also check for legacy "fixed-step" generator alongside canonical planner
    canonical = repo_root / "canonical_architecture" / "statutory_rescue.py"
    legacy_dir = repo_root / "app" / "services"
    if canonical.exists() and legacy_dir.exists():
        for cand in ("rescue_service.py", "rescue_planner.py"):
            p = legacy_dir / cand
            if p.exists():
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if "fixed" in text.lower() and "step" in text.lower():
                    findings.append(Finding(
                        "HIST-RESCUE-CONTRACT", str(p), 0, "WARN",
                        "Legacy fixed-step rescue generator still present alongside canonical "
                        "planner. Behaviour may diverge.",
                        "Either remove the legacy generator (after parity test passes) or wire "
                        "both to a shared step-builder.",
                    ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/historical_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC Historical Issues Re-verification ===")
    print(f"Repo: {repo_root}")
    print()

    findings: list[Finding] = []
    check_lbr_rules(repo_root, findings)
    check_dupkeys(repo_root, findings)
    check_or_true(repo_root, findings)
    check_vulndeps(repo_root, findings)
    check_dup_api_base(repo_root, findings)
    check_mig_drift(repo_root, findings)
    check_worker_module(repo_root, findings)
    check_rescue_contract(repo_root, findings)

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