#!/usr/bin/env python3
"""
Section K -- Database migrations, workers & operations audit.

Covers:
    DB-001  Repo migration head vs deployed DB revision may differ
    DB-002  Migrations succeed on clean DB + representative existing DB
    DB-003  ORM defaults, server defaults, migration defaults must agree
    OPS-001 Background workers - tenant scoping, retries, idempotency, recovery
    OPS-002 Scheduled jobs - registered, deployed, monitored
    OPS-003 Cleanup/maintenance tasks - verified implementation
    OPS-004 Failed/partial evaluations must not leave stale scores or audit records
    OPS-005 Integration tests must run against PostgreSQL test env
    OPS-006 Production secrets, CORS, security headers, deps, startup config

Usage:
    python scripts/verify_db_ops.py /path/to/nlc_platform_clean
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
    for sub in ("app", "canonical_architecture", "tests", "alembic", "migrations"):
        d = repo_root / sub
        if d.exists():
            targets.extend(p for p in d.rglob("*.py"))
    return sorted(targets)


def check_db_001(repo_root: Path, findings: list[Finding]) -> None:
    """DB-001: repo migration head vs deployed DB revision."""
    alembic_dir = repo_root / "alembic" / "versions"
    if not alembic_dir.exists():
        alembic_dir = repo_root / "migrations" / "versions"
    if not alembic_dir.exists():
        findings.append(Finding(
            "DB-001", "(alembic)", 0, "WARN",
            "No alembic/migrations/versions directory found. Cannot enumerate migration head.",
        ))
        return
    # find the highest revision
    revision_re = re.compile(r'^revision\s*[:=]\s*[\'"]([^\'"]+)[\'"]', re.M)
    down_re = re.compile(r'^down_revision\s*[:=]\s*[\'"]([^\'"]+)[\'"]', re.M)
    revisions: dict[str, str | None] = {}
    for p in alembic_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        rev_m = revision_re.search(text)
        down_m = down_re.search(text)
        if rev_m:
            revisions[rev_m.group(1)] = down_m.group(1) if down_m else None
    # find heads: revisions that are not anyone's down_revision
    down_targets = {d for d in revisions.values() if d}
    heads = [r for r in revisions if r not in down_targets]
    if len(heads) > 1:
        findings.append(Finding(
            "DB-001", "(alembic)", 0, "FAIL",
            f"Multiple migration heads detected: {heads}. Repo is in inconsistent state -- "
            f"run `alembic heads` locally and merge.",
            "Run `alembic merge -m merge_heads <head1> <head2>` and commit the merge revision.",
        ))
    elif len(heads) == 1:
        findings.append(Finding(
            "DB-001", "(alembic)", 0, "INFO",
            f"Single repo migration head: {heads[0]}. Compare to deployed DB revision (run "
            f"verify_rls.py for the DB-001 runtime check, OR run `alembic current` against the "
            f"production DB).",
        ))


def check_db_002(repo_root: Path, findings: list[Finding]) -> None:
    """DB-002: migrations succeed on clean DB + representative existing DB."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    clean_db_tests = []
    for p in test_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"alembic.*upgrade.*head|create_all|init_database|clean.*db.*test", text, re.I):
            clean_db_tests.append(p)
    if not clean_db_tests:
        findings.append(Finding(
            "DB-002", "(tests)", 0, "WARN",
            "No clean-DB migration test found. Cannot confirm migrations succeed on a fresh DB.",
            "Add tests/integration/test_migration_clean_db.py: spin up a fresh Postgres, "
            "run `alembic upgrade head`, assert no errors, assert all expected tables exist.",
        ))


def check_db_003(repo_root: Path, findings: list[Finding]) -> None:
    """DB-003: ORM defaults, server defaults, migration defaults must agree."""
    models_dir = repo_root / "app" / "models"
    alembic_dir = repo_root / "alembic" / "versions"
    if not (models_dir.exists() and alembic_dir.exists()):
        return
    # Pick transfer/restriction as the canonical case (TR-005)
    fields_to_check = [
        ("restriction", "transfer"),  # TR-005
        ("is_restricted", "transfer"),
        ("board_approval", "transfer"),
    ]
    for field_name, model_name in fields_to_check:
        orm_default = None
        server_default = None
        migration_default = None
        # ORM
        for p in models_dir.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in re.finditer(rf'\b{field_name}\b\s*=\s*(Column\([^)]+\)|Mapped\[[^\]]+\])', text):
                col_def = m.group(0)
                if "default=" in col_def:
                    d = re.search(r'default\s*=\s*([^,\)]+)', col_def)
                    if d:
                        orm_default = d.group(1).strip()
                if "server_default=" in col_def:
                    d = re.search(r'server_default\s*=\s*([^,\)]+)', col_def)
                    if d:
                        server_default = d.group(1).strip()
        # Migration
        for p in alembic_dir.rglob("*.py"):
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            for m in re.finditer(rf'\b{field_name}\b[^,)]*server_default\s*=\s*[\'"]?([^\'",)]+)', text):
                migration_default = m.group(1).strip()
                break
            if migration_default:
                break
        if orm_default is not None and server_default is not None and orm_default != server_default:
            findings.append(Finding(
                "DB-003", f"(models/{model_name}.{field_name})", 0, "FAIL",
                f"ORM default ({orm_default}) != server_default ({server_default}) for "
                f"{model_name}.{field_name}. Inserting without ORM will use a different default.",
                "Set both to the same value. Prefer server_default for DB-level guarantees.",
            ))
        elif migration_default is not None and orm_default is not None and migration_default != orm_default:
            findings.append(Finding(
                "DB-003", f"(models/{model_name}.{field_name})", 0, "FAIL",
                f"Migration default ({migration_default}) != ORM default ({orm_default}) for "
                f"{model_name}.{field_name}. Existing rows may have a different default than new "
                f"rows inserted via ORM.",
                "Update the migration to match the ORM default, OR backfill existing rows.",
            ))


def check_ops_001(repo_root: Path, findings: list[Finding]) -> None:
    """OPS-001: background workers - tenant scoping, retries, idempotency, recovery."""
    worker_dir = repo_root / "app" / "worker"
    if not worker_dir.exists():
        findings.append(Finding("OPS-001", "?", 0, "WARN",
                                "No app/worker directory; cannot check worker code."))
        return
    py_files = list(worker_dir.rglob("*.py"))
    has_retry = False
    has_idempotency = False
    has_tenant_scope = False
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"retry|backoff|max_retries|@retry", text, re.I):
            has_retry = True
        if re.search(r"idempot|already_processed|processed_keys|deduplicat", text, re.I):
            has_idempotency = True
        if re.search(r"company_id|tenant_id|app\.current_user_id", text, re.I):
            has_tenant_scope = True
    if not has_retry:
        findings.append(Finding(
            "OPS-001", "(worker)", 0, "WARN",
            "No retry/backoff logic detected in worker code. Background evaluation failures may "
            "not recover.",
            "Wrap evaluation tasks with a retry decorator (e.g. tenacity) with exponential backoff.",
        ))
    if not has_idempotency:
        findings.append(Finding(
            "OPS-001", "(worker)", 0, "WARN",
            "No idempotency key handling detected. Re-runs of the same evaluation will produce "
            "duplicate compliance_score rows.",
            "Use `target_company_id + rule_engine_version + snapshot_hash` as a unique key; "
            "skip if a row already exists for this combination.",
        ))
    if not has_tenant_scope:
        findings.append(Finding(
            "OPS-001", "(worker)", 0, "FAIL",
            "Worker code does not appear to set app.current_user_id before evaluating. RLS will "
            "return ZERO rows -- every worker-evaluated company will look compliant.",
            "Set `await db.execute(text('SET app.current_user_id = :id'), {'id': company_id})` "
            "at the start of every worker evaluation task.",
        ))


def check_ops_002(repo_root: Path, findings: list[Finding]) -> None:
    """OPS-002: scheduled jobs - registered, deployed, monitored."""
    py_files = collect_py_files(repo_root)
    scheduler_files = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"APScheduler|CeleryBeat|@scheduler\.|cron_trigger|add_job", text, re.I):
            scheduler_files.append(p)
    if not scheduler_files:
        findings.append(Finding(
            "OPS-002", "?", 0, "WARN",
            "No scheduler registration code detected. Scheduled tasks may not actually run.",
        ))
        return
    # Check for monitoring hooks
    has_monitoring = False
    for p in scheduler_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"health_check|/health|metrics|monitor|emit_metric", text, re.I):
            has_monitoring = True
    if not has_monitoring:
        findings.append(Finding(
            "OPS-002", str(scheduler_files[0]), 0, "WARN",
            "Scheduled jobs registered but no monitoring hook detected. Failed jobs may go "
            "unnoticed.",
            "Emit a metric (Prometheus counter) at task start/end. Add a /health endpoint that "
            "checks `last_run_at` for each scheduled job and reports STALE if overdue.",
        ))


def check_ops_003(repo_root: Path, findings: list[Finding]) -> None:
    """OPS-003: cleanup/maintenance tasks - verified implementation."""
    py_files = collect_py_files(repo_root)
    cleanup_files = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"cleanup|maintenance|purge|archive|prune", text, re.I) and (
            "def " in text or "async def" in text
        ):
            cleanup_files.append(p)
    if not cleanup_files:
        findings.append(Finding(
            "OPS-003", "?", 0, "INFO",
            "No cleanup/maintenance task detected. May be a real gap, or may be implemented "
            "externally (e.g. cron).",
        ))
    else:
        # check if there's a test for each cleanup task
        test_dir = repo_root / "tests"
        test_text = ""
        if test_dir.exists():
            for p in test_dir.rglob("*.py"):
                try:
                    test_text += p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
        for p in cleanup_files:
            name = p.stem
            if name not in test_text:
                findings.append(Finding(
                    "OPS-003", str(p), 0, "WARN",
                    f"Cleanup task {p.name} has no corresponding test in tests/.",
                    "Add a unit test that exercises the cleanup task against fixture data and "
                    "asserts the expected rows are removed/archived.",
                ))


def check_ops_004(repo_root: Path, findings: list[Finding]) -> None:
    """OPS-004: failed/partial evaluations must not leave stale scores."""
    py_files = list((repo_root / "app").rglob("*.py")) if (repo_root / "app").exists() else []
    evaluation_files = []
    for p in py_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"compliance_score|score_id|save.*score|commit.*score", text, re.I):
            evaluation_files.append(p)
    if not evaluation_files:
        return
    has_transaction = False
    has_status_field = False
    for p in evaluation_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if re.search(r"async with db\.begin\(\)|begin\(\)|transaction|rollback", text, re.I):
            has_transaction = True
        if re.search(r"evaluation_status|score_status|status\s*=.*(?:IN_PROGRESS|PENDING|FAILED|COMPLETED)", text, re.I):
            has_status_field = True
    if not has_transaction:
        findings.append(Finding(
            "OPS-004", "(score-write)", 0, "FAIL",
            "Score writes appear not to be wrapped in a DB transaction. Partial failures leave "
            "stale scores + missing audit records.",
            "Wrap every compliance_score INSERT/UPDATE in `async with db.begin():` so partial "
            "failures roll back atomically.",
        ))
    if not has_status_field:
        findings.append(Finding(
            "OPS-004", "(score-write)", 0, "WARN",
            "No visible evaluation_status field. Cannot detect partial evaluations from the "
            "data alone.",
            "Add an `evaluation_status` enum column: PENDING / IN_PROGRESS / COMPLETED / FAILED. "
            "Set to IN_PROGRESS at start; COMPLETED only after audit row is committed.",
        ))


def check_ops_005(repo_root: Path, findings: list[Finding]) -> None:
    """OPS-005: integration tests must actually run against PostgreSQL test env."""
    test_dir = repo_root / "tests"
    if not test_dir.exists():
        return
    integration_dir = test_dir / "integration"
    if not integration_dir.exists():
        return
    skipped = 0
    for p in integration_dir.rglob("*.py"):
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        # pytest.mark.skip / skipif / unittest.skip
        skipped += len(re.findall(r"@pytest\.mark\.skip|@pytest\.mark\.skipif|@unittest\.skip", text))
    if skipped > 0:
        findings.append(Finding(
            "OPS-005", str(integration_dir), 0, "WARN",
            f"{skipped} integration test(s) marked skip/skipif. Integration coverage is "
            f"artificially inflated.",
            "Remove the skips. If skipping was due to DB connection issues, fix the test DB "
            "fixture instead of skipping the test.",
        ))


def check_ops_006(repo_root: Path, findings: list[Finding]) -> None:
    """OPS-006: production secrets, CORS, security headers, deps."""
    config_files = []
    for pat in ("app/core/config.py", "app/main.py", "pyproject.toml", "requirements.txt",
                ".env.example", "docker-compose.yml", "Dockerfile"):
        p = repo_root / pat
        if p.exists():
            config_files.append(p)
    if not config_files:
        return
    # check for hardcoded secrets
    secret_re = re.compile(r'(secret_key|jwt_secret|database_url|api_key|password)\s*[=:]\s*[\'"]([^\'"]{8,})[\'"]',
                           re.I)
    for p in config_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for m in secret_re.finditer(text):
            value = m.group(2)
            if value not in ("change-me", "your-secret-here", "${SECRET_KEY}", "${JWT_SECRET}",
                             "${DATABASE_URL}", "${API_KEY}"):
                lineno = text[:m.start()].count("\n") + 1
                findings.append(Finding(
                    "OPS-006", str(p), lineno, "FAIL",
                    f"Hardcoded secret-like value for {m.group(1)} in {p.name}: `{value[:20]}...`",
                    "Move all secrets to env vars. Never commit real values.",
                ))
    # CORS check
    for p in config_files:
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if "allow_origins" in text and ("*" in text or '["*"]' in text):
            findings.append(Finding(
                "OPS-006", str(p), 0, "FAIL",
                f"CORS allow_origins contains '*' in {p.name}. Cross-origin requests from any "
                f"host are accepted.",
                "Restrict to explicit allowed origins list (e.g. https://app.example.com).",
            ))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("repo", help="Path to nlc_platform_clean repository root.")
    p.add_argument("--output", default="/home/z/my-project/scripts/db_ops_report.json")
    args = p.parse_args()

    repo_root = Path(args.repo).resolve()
    if not repo_root.exists():
        print(f"ERROR: repo path does not exist: {repo_root}", file=sys.stderr)
        return 2

    print(f"=== NLC DB / OPS Audit ===")
    print(f"Repo: {repo_root}")
    print()

    findings: list[Finding] = []
    check_db_001(repo_root, findings)
    check_db_002(repo_root, findings)
    check_db_003(repo_root, findings)
    check_ops_001(repo_root, findings)
    check_ops_002(repo_root, findings)
    check_ops_003(repo_root, findings)
    check_ops_004(repo_root, findings)
    check_ops_005(repo_root, findings)
    check_ops_006(repo_root, findings)

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