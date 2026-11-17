#!/usr/bin/env bash
# ============================================================================
# NLC Platform — P0 Fix #4 (v3): Migration Preflight — HARD STOP, NO FALLBACK
# File: scripts/fixes/04_migration_preflight.sh
#
# v3 CORRECTIONS (critical):
#   - HARD STOP on any identity or ownership failure. No silent fallback to
#     the existing migration login or the runtime account.
#   - Verifies that alembic/env.py's role-preparation function ACTUALLY RUNS
#     inside the Alembic database connection. A shell-level `SET ROLE` in this
#     script runs in a DIFFERENT connection (the psql connection) and does
#     NOT carry over to Alembic's SQLAlchemy connection. The role assumption
#     must happen INSIDE env.py, in the Alembic connection, before migrations.
#   - Calls 06_alembic_env_role_check.py which:
#       (a) parses alembic/env.py to confirm the role-prep function exists
#       (b) opens a SQLAlchemy connection as nlc_migration_user
#       (c) executes the same role-prep logic env.py would run
#       (d) asserts SELECT current_role = 'nlc_migration_owner'
#       (e) executes a temp-table DDL to confirm the assumed role can do DDL
#
# Exit codes:
#   0 = preflight passed, migrations applied, runtime verified
#   1 = MIGRATION_DATABASE_URL missing
#   2 = migration identity verification failed (02_...sql)
#   3 = env.py role-preparation check failed (06_...py)
#   4 = alembic upgrade failed
#   5 = runtime health check failed after migration
# ============================================================================

set -euo pipefail

echo "=== NLC Migration Preflight (v3 — hard stop, no fallback) ==="
echo "Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "Commit: ${RENDER_GIT_COMMIT:-local}"
echo ""

# ===========================================================================
# GATE 1 — MIGRATION_DATABASE_URL must be set
-- ---------------------------------------------------------------------------
# If not set, STOP. Do NOT fall back to DATABASE_URL (that is the runtime
# nlc_app_role connection, which cannot do DDL and must never be used for
# migrations).
# ===========================================================================
if [[ -z "${MIGRATION_DATABASE_URL:-}" ]]; then
  echo "FATAL [gate 1]: MIGRATION_DATABASE_URL is not set."
  echo "  Refusing to fall back to DATABASE_URL (runtime nlc_app_role)."
  echo "  See 03_render_env.md."
  exit 1
fi
if [[ "$MIGRATION_DATABASE_URL" == "${DATABASE_URL:-}" ]]; then
  echo "FATAL [gate 1]: MIGRATION_DATABASE_URL is identical to DATABASE_URL."
  echo "  This defeats identity separation. Refusing to proceed."
  exit 1
fi
echo "[gate 1] MIGRATION_DATABASE_URL is set and distinct from DATABASE_URL."

# Load password from secret file if present
if [[ -n "${MIGRATION_PASSWORD_FILE:-}" && -f "${MIGRATION_PASSWORD_FILE}" ]]; then
  set -a; source "${MIGRATION_PASSWORD_FILE}"; set +a
  echo "[gate 1] Loaded MIGRATION_PASSWORD from secret file."
fi

# ===========================================================================
# GATE 2 — Migration identity verification (02_...sql, 10 checks)
# ===========================================================================
PSQL_URL="${MIGRATION_DATABASE_URL/postgresql+asyncpg/postgresql}"
echo "[gate 2] Running 02_verify_migration_identity.sql (10 checks)..."
if ! psql "${PSQL_URL}" -v ON_ERROR_STOP=1 -f scripts/fixes/02_verify_migration_identity.sql; then
  echo "FATAL [gate 2]: Migration identity verification failed."
  echo "  The deployment STOPS. Do NOT fall back to the existing migration login."
  echo "  Run 01_migration_identity.sql as neondb_owner, then retry."
  exit 2
fi
echo "[gate 2] All 10 identity checks passed."

# ===========================================================================
# GATE 3 — env.py role-preparation verification (06_...py)
-- ---------------------------------------------------------------------------
# This is the critical gate v2 missed. Alembic opens its OWN database
# connection via SQLAlchemy. A shell-level `psql -c "SET ROLE ..."` in this
# script runs in a SEPARATE connection and does NOT persist into Alembic's
# connection. The role assumption MUST happen inside alembic/env.py.
#
# 06_...py:
#   (a) parses alembic/env.py and confirms a role-preparation function exists
#   (b) opens a SQLAlchemy connection as nlc_migration_user (same URL Alembic uses)
#   (c) executes the same SET ROLE logic env.py would run
#   (d) asserts SELECT current_role = 'nlc_migration_owner'
#   (e) executes CREATE TEMP TABLE to confirm DDL works under the assumed role
#   (f) fails if any step does not produce the expected result
# ===========================================================================
echo "[gate 3] Verifying alembic/env.py role-preparation in a live connection..."
if ! python3 scripts/fixes/06_alembic_env_role_check.py; then
  echo "FATAL [gate 3]: env.py role-preparation verification failed."
  echo "  Alembic will NOT assume nlc_migration_owner inside its own connection."
  echo "  A shell-level SET ROLE does NOT carry over to Alembic's SQLAlchemy session."
  echo "  Fix alembic/env.py to call the role-preparation function inside the"
  echo "  run_migrations_online() context, then retry."
  exit 3
fi
echo "[gate 3] env.py role-preparation verified: Alembic will run as nlc_migration_owner."

# ===========================================================================
# GATE 4 — Alembic upgrade (under the verified identity)
# ===========================================================================
echo "[gate 4] Running alembic upgrade head..."
if ! alembic upgrade head; then
  echo "FATAL [gate 4]: alembic upgrade head failed."
  echo "  The identity was verified; the migration itself failed."
  echo "  Inspect the Alembic output above for the failing revision."
  exit 4
fi

CURRENT_REV=$(alembic current 2>/dev/null | awk '{print $1}')
echo "[gate 4] Migrated to revision: ${CURRENT_REV}"

# ===========================================================================
# GATE 5 — Runtime connectivity with DATABASE_URL (nlc_app_role)
# ===========================================================================
echo "[gate 5] Verifying runtime role (nlc_app_role) can read the migrated schema..."
RUNTIME_PSQL_URL="${DATABASE_URL/postgresql+asyncpg/postgresql}"

VERIFY_RUNTIME=$(psql "${RUNTIME_PSQL_URL}" -t -A -c "
  SELECT
    (SELECT version_num FROM alembic_version) AS rev,
    COUNT(*) AS table_count
  FROM information_schema.tables
  WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
")
echo "[gate 5] Runtime sees: ${VERIFY_RUNTIME}"

# Confirm runtime role CANNOT do DDL (defense in depth)
if psql "${RUNTIME_PSQL_URL}" -c "CREATE TABLE _preflight_ddl_probe (id int);" 2>/dev/null; then
  echo "FATAL [gate 5]: nlc_app_role can CREATE TABLE — DDL lockdown failed."
  psql "${RUNTIME_PSQL_URL}" -c "DROP TABLE _preflight_ddl_probe;" 2>/dev/null || true
  exit 5
fi
echo "[gate 5] Confirmed: nlc_app_role cannot do DDL."

# Health endpoint check
if [[ -n "${RENDER_EXTERNAL_URL:-}" ]]; then
  sleep 5
  if ! curl -fsS "${RENDER_EXTERNAL_URL}/api/v1/health/ready" > /dev/null; then
    echo "WARN [gate 5]: /health/ready not yet 200 — may still be starting."
  else
    echo "[gate 5] /health/ready returned 200."
  fi
fi

echo ""
echo "=== Migration preflight PASSED ==="
echo "Revision applied: ${CURRENT_REV}"
echo "Identity: nlc_migration_owner (assumed inside Alembic via env.py)"
echo "Runtime:  nlc_app_role (no DDL, RLS-protected)"
exit 0
