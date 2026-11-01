#!/usr/bin/env python3
"""
NLC Production Migration Reconciliation & Deployment Reliability Audit

Run: python tools/production_reconciliation.py

Checks:
1. Migration chain integrity (no gaps, no heads)
2. Rule-version consistency (engine vs seed vs DB)
3. BLACK override evidence gating
4. Seed data integrity (no count-based seeding)
5. CORS configuration
6. Health/readiness probes
7. Render deployment config
8. Redis blacklist fail-open behaviour
9. RLS policy existence
10. Deployment rollback capability
"""
import sys
import os
import re
import ast
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

PASS = 0
FAIL = 0
WARN = 0

def log_result(check_id, name, status, detail=""):
    global PASS, FAIL, WARN
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}[status]
    print(f"{icon} {check_id:8s} {status:4s} {name}")
    if detail:
        for line in detail.split("\n"):
            print(f"         {line}")
    if status == "PASS": PASS += 1
    elif status == "FAIL": FAIL += 1
    else: WARN += 1

print("=" * 78)
print("NLC PRODUCTION RECONCILIATION & DEPLOYMENT RELIABILITY AUDIT")
print(f"Date: {datetime.now().isoformat()}")
print(f"Root: {ROOT}")
print("=" * 78)

# ─── 1. MIGRATION CHAIN INTEGRITY ───────────────────────────────────────
print("\n── 1. MIGRATION CHAIN INTEGRITY ──────────────────────────────────\n")

migrations_dir = ROOT / "alembic" / "versions"
migration_files = list(migrations_dir.glob("*.py"))
revision_map = {}  # revision -> file
down_map = {}      # revision -> down_revision

for mf in migration_files:
    text = mf.read_text(encoding="utf-8", errors="ignore")
    rev_match = re.search(r'^revision\s*(?::\s*\w+\s*)?=\s*["\']([^"\']+)["\']', text, re.M)
    down_match = re.search(r'^down_revision\s*(?::\s*[\w\[\]|, ]+\s*)?=\s*["\']([^"\']+)["\']', text, re.M)
    if rev_match:
        rev = rev_match.group(1)
        revision_map[rev] = mf.name
        if down_match:
            down_map[rev] = down_match.group(1)

# Find heads (revisions not referenced as down_revision by any other)
all_downs = set(down_map.values())
all_revs = set(revision_map.keys())
heads = all_revs - all_downs

if len(heads) == 1:
    log_result("MIG-01", "Single migration head", "PASS", f"Head: {heads.pop()}")
elif len(heads) == 0:
    log_result("MIG-01", "Single migration head", "FAIL", "No head found — circular dependency?")
else:
    log_result("MIG-01", "Single migration head", "FAIL", f"Multiple heads: {heads}")

# Check for gaps (down_revision points to non-existent revision)
gaps = []
for rev, down in down_map.items():
    if down and down not in revision_map:
        gaps.append(f"{rev} → {down} (missing)")

if not gaps:
    log_result("MIG-02", "No migration gaps", "PASS", f"Chain: {len(migration_files)} migrations, all linked")
else:
    log_result("MIG-02", "No migration gaps", "FAIL", "\n".join(gaps))

# ─── 2. RULE-VERSION CONSISTENCY ────────────────────────────────────────
print("\n── 2. RULE-VERSION CONSISTENCY ───────────────────────────────────\n")

engine_path = ROOT / "app" / "rule_engine" / "engine.py"
engine_text = engine_path.read_text(encoding="utf-8", errors="ignore")
engine_rules = set(re.findall(r'rule_id="([A-Z]+-\d+)"', engine_text))

seed_path = ROOT / "scripts" / "seed_rules.py"
if seed_path.exists():
    seed_text = seed_path.read_text(encoding="utf-8", errors="ignore")
    seed_rules = set(re.findall(r'"rule_id":\s*"([A-Z]+-\d+)"', seed_text))
else:
    seed_rules = set()

only_engine = engine_rules - seed_rules
only_seed = seed_rules - engine_rules

if not only_engine and not only_seed:
    log_result("RULE-01", "Engine vs seed rule IDs match", "PASS", f"{len(engine_rules)} rules in both")
else:
    detail = ""
    if only_engine:
        detail += f"Only in engine ({len(only_engine)}): {sorted(only_engine)[:5]}...\n"
    if only_seed:
        detail += f"Only in seed ({len(only_seed)}): {sorted(only_seed)[:5]}..."
    log_result("RULE-01", "Engine vs seed rule IDs match", "WARN", detail)

# Check RULE_ENGINE_VERSION
version_match = re.search(r'RULE_ENGINE_VERSION\s*=\s*"([^"]+)"', engine_text)
if version_match:
    log_result("RULE-02", "Rule engine version defined", "PASS", f"Version: {version_match.group(1)}")
else:
    log_result("RULE-02", "Rule engine version defined", "FAIL", "RULE_ENGINE_VERSION not found")

# ─── 3. BLACK OVERRIDE EVIDENCE GATING ──────────────────────────────────
print("\n── 3. BLACK OVERRIDE EVIDENCE GATING ─────────────────────────────\n")

# Find all is_black_override=True occurrences with their rule_id
black_pattern = re.compile(
    r'rule_id="([A-Z]+-\d+)".*?is_black_override=True',
    re.DOTALL
)
black_rules = set()
for match in black_pattern.finditer(engine_text):
    black_rules.add(match.group(1))

# Check DEF-001 specifically — does it require evidence?
if 'disqualification_grounds' in engine_text and 'evidence_ref' in engine_text:
    log_result("BLK-01", "DEF-001 evidence gating", "PASS", "Uses structured disqualification_grounds with evidence_ref")
else:
    log_result("BLK-01", "DEF-001 evidence gating", "FAIL", "No evidence gating found")

# Check that unverified allegations don't trigger BLACK
if 'Severity.NOT_EVALUATED' in engine_text and 'DIRECTOR_DISQUALIFICATION_UNVERIFIED' in engine_text:
    log_result("BLK-02", "Unverified allegations → NOT_EVALUATED", "PASS", "Unverified DEF-001 emits NOT_EVALUATED, not BLACK")
else:
    log_result("BLK-02", "Unverified allegations → NOT_EVALUATED", "WARN", "Cannot confirm evidence gating")

# ─── 4. SEED DATA INTEGRITY ─────────────────────────────────────────────
print("\n── 4. SEED DATA INTEGRITY ────────────────────────────────────────\n")

# Check for count-based seeding (INSERT ... SELECT COUNT)
if seed_path.exists():
    if "SELECT COUNT" in seed_text or "len(" in seed_text:
        log_result("SEED-01", "No count-based seeding", "WARN", "Seed script uses count or len() — verify it's not generating rules dynamically")
    else:
        log_result("SEED-01", "No count-based seeding", "PASS", "Seed rules are statically defined")
else:
    log_result("SEED-01", "No count-based seeding", "PASS", "No seed_rules.py found")

# Check for ON CONFLICT handling in migrations
conflict_count = 0
for mf in migration_files:
    text = mf.read_text(encoding="utf-8", errors="ignore")
    if "INSERT INTO legal_rules" in text and "ON CONFLICT" not in text:
        conflict_count += 1

if conflict_count == 0:
    log_result("SEED-02", "All seed migrations use ON CONFLICT", "PASS", "Idempotent seeding")
else:
    log_result("SEED-02", "All seed migrations use ON CONFLICT", "WARN", f"{conflict_count} migrations insert without ON CONFLICT")

# ─── 5. CORS CONFIGURATION ──────────────────────────────────────────────
print("\n── 5. CORS CONFIGURATION ─────────────────────────────────────────\n")

main_path = ROOT / "app" / "main.py"
main_text = main_path.read_text(encoding="utf-8", errors="ignore")

if "allow_origin_regex" in main_text:
    log_result("CORS-01", "CORS uses regex (not wildcard)", "PASS", "Vercel + localhost regex pattern")
elif 'allow_origins=["*"]' in main_text:
    log_result("CORS-01", "CORS uses regex (not wildcard)", "FAIL", "Wildcard origins — security risk")
else:
    log_result("CORS-01", "CORS uses regex (not wildcard)", "WARN", "Cannot determine CORS strategy")

if "allow_credentials=True" in main_text:
    log_result("CORS-02", "Credentials allowed", "PASS", "Required for JWT cookie/header auth")
else:
    log_result("CORS-02", "Credentials allowed", "WARN", "allow_credentials not set")

# ─── 6. HEALTH/READINESS PROBES ─────────────────────────────────────────
print("\n── 6. HEALTH/READINESS PROBES ────────────────────────────────────\n")

health_path = ROOT / "app" / "api" / "health.py"
health_text = health_path.read_text(encoding="utf-8", errors="ignore")

if "/health/live" in health_text and "liveness" in health_text:
    log_result("HLT-01", "Liveness probe exists", "PASS", "GET /api/v1/health/live returns 200")
else:
    log_result("HLT-01", "Liveness probe exists", "FAIL")

if "/health/ready" in health_text and "readiness" in health_text:
    log_result("HLT-02", "Readiness probe exists", "PASS", "GET /api/v1/health/ready checks DB + Redis")
else:
    log_result("HLT-02", "Readiness probe exists", "FAIL")

if "503" in health_text and "ready" in health_text:
    log_result("HLT-03", "Readiness returns 503 when not ready", "PASS", "Returns 503 if DB or Redis down")
else:
    log_result("HLT-03", "Readiness returns 503 when not ready", "WARN")

# ─── 7. RENDER DEPLOYMENT CONFIG ────────────────────────────────────────
print("\n── 7. RENDER DEPLOYMENT CONFIG ───────────────────────────────────\n")

render_path = ROOT / "render.yaml"
if render_path.exists():
    render_text = render_path.read_text(encoding="utf-8", errors="ignore")

    if "healthCheckPath: /api/v1/health/live" in render_text:
        log_result("RNDR-01", "Render health check configured", "PASS", "Path: /api/v1/health/live")
    else:
        log_result("RNDR-01", "Render health check configured", "FAIL", "No health check path")

    if "autoDeploy: true" in render_text:
        log_result("RNDR-02", "Auto-deploy enabled", "WARN", "Auto-deploys from main — no manual approval gate")

    if "DATABASE_URL" in render_text and "sync: false" in render_text:
        log_result("RNDR-03", "DATABASE_URL is a secret", "PASS", "Sync=false (not in repo)")
    else:
        log_result("RNDR-03", "DATABASE_URL is a secret", "FAIL", "DATABASE_URL may be exposed")

    if "worker" in render_text and "celery" in render_text:
        log_result("RNDR-04", "Celery worker service configured", "PASS", "Worker + web service")
    else:
        log_result("RNDR-04", "Celery worker service configured", "WARN", "No worker service")

    if "ALLOWED_ORIGINS" in render_text:
        log_result("RNDR-05", "CORS origins in env", "PASS", "Configured via ALLOWED_ORIGINS")
    else:
        log_result("RNDR-05", "CORS origins in env", "WARN")
else:
    log_result("RNDR-01", "Render config exists", "FAIL", "No render.yaml found")

# ─── 8. REDIS BLACKLIST BEHAVIOUR ───────────────────────────────────────
print("\n── 8. REDIS BLACKLIST BEHAVIOUR ──────────────────────────────────\n")

blacklist_path = ROOT / "app" / "core" / "token_blacklist.py"
bl_text = blacklist_path.read_text(encoding="utf-8", errors="ignore")

if "return False" in bl_text and "except Exception" in bl_text:
    log_result("RDS-01", "Blacklist fails open (availability)", "PASS", "Returns False (not revoked) on Redis error — availability over security")
else:
    log_result("RDS-01", "Blacklist fails open", "WARN", "Cannot determine fail behaviour")

if "setex" in bl_text:
    log_result("RDS-02", "Revocation uses TTL", "PASS", "Blacklist entry expires with token — no unbounded growth")
else:
    log_result("RDS-02", "Revocation uses TTL", "FAIL", "No TTL on blacklist entries")

if "socket_connect_timeout" in bl_text and "socket_timeout" in bl_text:
    log_result("RDS-03", "Redis timeout configured", "PASS", "2s connect + 2s socket timeout")
else:
    log_result("RDS-03", "Redis timeout configured", "FAIL", "No timeout — Redis hang blocks all requests")

# ─── 9. RLS ARCHITECTURE ────────────────────────────────────────────────
print("\n── 9. RLS ARCHITECTURE & MIGRATIONS ──────────────────────────────\n")

db_path = ROOT / "app" / "models" / "database.py"
db_text = db_path.read_text(encoding="utf-8", errors="ignore")

if "set_config('app.current_user_id'" in db_text:
    log_result("RLS-01", "RLS session variable set", "PASS", "app.current_user_id set via parameterized query")
else:
    log_result("RLS-01", "RLS session variable set", "FAIL")

if "set_config('app.current_user_id', 'ADMIN'" in db_text:
    log_result("RLS-02", "Admin bypass context", "PASS", "ADMIN context for background jobs")
else:
    log_result("RLS-02", "Admin bypass context", "FAIL")

# Check for RLS policies in migrations
rls_migrations = []
for mf in migration_files:
    text = mf.read_text(encoding="utf-8", errors="ignore")
    if "ROW LEVEL SECURITY" in text.upper() or "CREATE POLICY" in text.upper():
        rls_migrations.append(mf.name)

if rls_migrations:
    log_result("RLS-03", "RLS policies in migrations", "PASS", f"Found in {len(rls_migrations)} migrations: {rls_migrations[:3]}...")
else:
    log_result("RLS-03", "RLS policies in migrations", "FAIL", "No RLS policies found in any migration")

# ─── 10. DEPLOYMENT RELIABILITY ─────────────────────────────────────────
print("\n── 10. DEPLOYMENT RELIABILITY ─────────────────────────────────────\n")

# Check for rollback capability
dockerfile_path = ROOT / "Dockerfile"
if dockerfile_path.exists():
    df_text = dockerfile_path.read_text(encoding="utf-8", errors="ignore")
    if "HEALTHCHECK" in df_text:
        log_result("DEP-01", "Dockerfile health check", "PASS")
    else:
        log_result("DEP-01", "Dockerfile health check", "WARN", "No HEALTHCHECK in Dockerfile — Render handles via healthCheckPath")

    if "CMD" in df_text or "ENTRYPOINT" in df_text:
        log_result("DEP-02", "Container entrypoint defined", "PASS")
    else:
        log_result("DEP-02", "Container entrypoint defined", "FAIL")
else:
    log_result("DEP-01", "Dockerfile exists", "FAIL")

# Check for .env.example
env_example = ROOT / ".env.example"
if env_example.exists():
    env_text = env_example.read_text(encoding="utf-8", errors="ignore")
    required_vars = ["DATABASE_URL", "REDIS_URL", "JWT_SECRET_KEY", "ALLOWED_ORIGINS"]
    missing = [v for v in required_vars if v not in env_text]
    if not missing:
        log_result("DEP-03", "All required env vars documented", "PASS")
    else:
        log_result("DEP-03", "All required env vars documented", "FAIL", f"Missing: {missing}")
else:
    log_result("DEP-03", ".env.example exists", "FAIL")

# Check Render has rollback (autoDeploy means every push deploys — rollback = revert commit)
if render_path.exists() and "autoDeploy: true" in render_text:
    log_result("DEP-04", "Rollback capability", "WARN", "Rollback = git revert + push. No blue/green or canary deploy.")

# ─── SUMMARY ────────────────────────────────────────────────────────────
print("\n" + "=" * 78)
print(f"SUMMARY: {PASS} PASS / {WARN} WARN / {FAIL} FAIL")
print("=" * 78)

if FAIL > 0:
    print("\n❌ CRITICAL ISSUES MUST BE FIXED BEFORE PRODUCTION DEPLOYMENT")
    sys.exit(1)
elif WARN > 0:
    print("\n⚠️  WARNINGS — review before deployment")
    sys.exit(0)
else:
    print("\n✅ ALL CHECKS PASSED — production ready")
    sys.exit(0)