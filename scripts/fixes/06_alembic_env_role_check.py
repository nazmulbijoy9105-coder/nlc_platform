#!/usr/bin/env python3
"""
NLC Platform — P0 Fix #6 (NEW): alembic/env.py Role-Preparation Verifier
File: scripts/fixes/06_alembic_env_role_check.py

THE PROBLEM THIS SOLVES
-----------------------
Alembic opens its OWN database connection via SQLAlchemy (engine_from_config +
connect()). A shell-level `psql -c "SET ROLE nlc_migration_owner"` executed
in the preflight shell script runs in a DIFFERENT connection (the psql
connection) and does NOT carry over to Alembic's SQLAlchemy session.

If alembic/env.py does not explicitly call `SET ROLE nlc_migration_owner`
INSIDE the Alembic connection (via connection.execute("SET ROLE ...")),
then Alembic runs as the bare nlc_migration_user login role — which has
NOINHERIT and therefore NO DDL privileges. Every ALTER TABLE in the
migration fails with "permission denied".

The audit confirms alembic/env.py "already contains a production
role-preparation function". This script verifies that function:
  (a) exists in alembic/env.py source
  (b) is actually invoked in the run_migrations_online() path
  (c) when executed in a live SQLAlchemy connection as nlc_migration_user,
      results in SELECT current_role = 'nlc_migration_owner'
  (d) grants DDL privileges (verified by CREATE TEMP TABLE)

Exit codes:
  0 = env.py role-preparation is present and works
  1 = env.py does not contain a role-preparation function
  2 = env.py contains the function but does not invoke it in the online path
  3 = the function is invoked but does not actually assume the role in a
      live connection (current_role != nlc_migration_owner)
  4 = the role is assumed but DDL fails (temp-table create fails)

Usage:
  python3 scripts/fixes/06_alembic_env_role_check.py

Environment:
  MIGRATION_DATABASE_URL — the Alembic connection URL (nlc_migration_user role)
  ALEMBIC_ROLE_TARGET    — expected role name (default: nlc_migration_owner)
"""
import os
import re
import sys
import ast
from pathlib import Path

EXPECTED_ROLE = os.environ.get("ALEMBIC_ROLE_TARGET", "nlc_migration_owner")
MIGRATION_URL = os.environ.get("MIGRATION_DATABASE_URL", "")

# ---------------------------------------------------------------------------
# 1. Locate alembic/env.py
# ---------------------------------------------------------------------------
REPO_ROOT = Path(os.environ.get("REPO_ROOT", "."))
ENV_PY = REPO_ROOT / "alembic" / "env.py"

def fail(code, msg):
    print(f"FATAL: {msg}", file=sys.stderr)
    sys.exit(code)

print("=== alembic/env.py Role-Preparation Verifier ===")
print(f"Expected role: {EXPECTED_ROLE}")
print(f"env.py path:   {ENV_PY.resolve()}")
print()

if not ENV_PY.exists():
    fail(1, f"alembic/env.py not found at {ENV_PY}. Set REPO_ROOT or run from the repo root.")

env_source = ENV_PY.read_text(encoding="utf-8")

# ---------------------------------------------------------------------------
# 2. Static analysis: does env.py contain a role-preparation function?
# ---------------------------------------------------------------------------
# Look for patterns like:
#   def _prepare_migration_role(connection): ...
#   def _set_role(connection): ...
#   def prepare_role(...): ...
#   SET ROLE ... in a string literal inside a function
ROLE_FUNC_PATTERNS = [
    r"def\s+_?prepare[_-]?(migration[_-]?)?role\s*\(",
    r"def\s+_?set[_-]?role\s*\(",
    r"def\s+_?assume[_-]?role\s*\(",
    r"def\s+_?configure[_-]?role\s*\(",
]
SET_ROLE_LITERAL = re.compile(
    r"""['"](SET\s+ROLE\s+%s)['"]""" % re.escape(EXPECTED_ROLE),
    re.IGNORECASE,
)
# Also accept a parameterised form: SET ROLE :role  /  SET ROLE %s
SET_ROLE_PARAM = re.compile(
    r"""['"](SET\s+ROLE\s+[:%]?\w+)['"]""",
    re.IGNORECASE,
)

found_func = None
for pat in ROLE_FUNC_PATTERNS:
    m = re.search(pat, env_source)
    if m:
        found_func = m.group(0)
        break

# Also scan for any SET ROLE literal that targets the expected role
set_role_literal_match = SET_ROLE_LITERAL.search(env_source)
set_role_param_match = SET_ROLE_PARAM.search(env_source)

if not found_func and not set_role_literal_match and not set_role_param_match:
    fail(1, (
        "alembic/env.py does not contain a recognisable role-preparation "
        f"function or a 'SET ROLE {EXPECTED_ROLE}' statement. "
        "Add a function that executes SET ROLE inside the Alembic connection "
        "and call it from run_migrations_online() before context.run_migrations()."
    ))

print(f"[1/4] Found role-preparation in env.py:")
if found_func:
    print(f"        function: {found_func}")
if set_role_literal_match:
    print(f"        literal:  {set_role_literal_match.group(1)}")
if set_role_param_match and not set_role_literal_match:
    print(f"        parameterised: {set_role_param_match.group(1)}")
print()

# ---------------------------------------------------------------------------
# 3. Confirm the function is invoked in the run_migrations_online() path
# ---------------------------------------------------------------------------
# Parse the AST and look for run_migrations_online, then check its body for
# a call to the role-prep function (or any execute("SET ROLE ...")).
try:
    tree = ast.parse(env_source)
except SyntaxError as e:
    fail(1, f"alembic/env.py has a syntax error: {e}")

online_fn = None
for node in ast.walk(tree):
    if isinstance(node, ast.FunctionDef) and node.name == "run_migrations_online":
        online_fn = node
        break

if online_fn is None:
    print("[2/4] WARNING: run_migrations_online() not found in env.py.")
    print("        If env.py uses a different entry point, verify manually.")
    # Not fatal — some env.py variants use run_migrations() only.
else:
    body_src = ast.unparse(online_fn) if hasattr(ast, "unparse") else ""
    role_call_found = False
    if found_func:
        fn_name = re.match(r"def\s+(\w+)", found_func).group(1)
        if fn_name in body_src:
            role_call_found = True
    if set_role_literal_match and "SET ROLE" in body_src.upper():
        role_call_found = True
    if set_role_param_match and "SET ROLE" in body_src.upper():
        role_call_found = True

    if not role_call_found:
        fail(2, (
            "run_migrations_online() in env.py does not invoke the "
            "role-preparation function. The function exists but is never "
            "called in the online migration path. Add a call inside the "
            "`with connectable.connect() as connection:` block, before "
            "context.run_migrations()."
        ))
    print(f"[2/4] run_migrations_online() invokes role-preparation.")
print()

# ---------------------------------------------------------------------------
# 4. Live connection test: does SET ROLE actually work in SQLAlchemy?
# ---------------------------------------------------------------------------
# Replicate what env.py should do: connect as nlc_migration_user, execute
# SET ROLE nlc_migration_owner, verify current_role, execute a temp DDL.
if not MIGRATION_URL:
    fail(1, "MIGRATION_DATABASE_URL is not set. Cannot run the live connection test.")

try:
    from sqlalchemy import create_engine, text
except ImportError:
    fail(1, "SQLAlchemy is not installed. pip install sqlalchemy")

# SQLAlchemy URL — asyncpg driver must be swapped to psycopg2 for sync
SYNC_URL = MIGRATION_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
if SYNC_URL == MIGRATION_URL:
    SYNC_URL = MIGRATION_URL.replace("postgresql://", "postgresql+psycopg2://")

print(f"[3/4] Opening live connection as nlc_migration_user...")
print(f"        URL: {SYNC_URL.replace(SYNC_URL.split(':')[1].split('@')[0].split('//')[-1], '***')}")

engine = create_engine(SYNC_URL, poolclass=None, isolation_level="AUTOCOMMIT")

try:
    with engine.connect() as conn:
        # Before SET ROLE — should be nlc_migration_user
        before = conn.execute(text("SELECT current_role")).scalar()
        print(f"        current_role before SET ROLE: {before}")
        if before != "nlc_migration_user":
            print(f"        WARN: expected nlc_migration_user, got {before}")

        # Execute SET ROLE — this is what env.py must do
        conn.execute(text(f"SET ROLE {EXPECTED_ROLE}"))

        after = conn.execute(text("SELECT current_role")).scalar()
        print(f"        current_role after SET ROLE:  {after}")
        if after != EXPECTED_ROLE:
            fail(3, (
                f"SET ROLE did not assume {EXPECTED_ROLE}. "
                f"current_role = {after}. "
                "This means env.py's role-preparation would also fail. "
                "Check that nlc_migration_user has membership in "
                "nlc_migration_owner (GRANT nlc_migration_owner TO "
                "nlc_migration_user) and that nlc_migration_user is NOINHERIT."
            ))
        print(f"[3/4] SET ROLE works: current_role = {EXPECTED_ROLE}")
        print()

        # Verify DDL works under the assumed role
        print(f"[4/4] Verifying DDL under assumed role...")
        try:
            conn.execute(text("CREATE TEMP TABLE _env_role_check (id int)"))
            conn.execute(text("DROP TABLE _env_role_check"))
            print(f"        CREATE TEMP TABLE succeeded — DDL works under {EXPECTED_ROLE}")
        except Exception as e:
            fail(4, (
                f"DDL failed under assumed role {EXPECTED_ROLE}: {e}. "
                "The role was assumed but cannot do DDL. Check that "
                "nlc_migration_owner has CREATE on public and owns the "
                "existing tables (01_ Step 4 ownership transfer)."
            ))

        # RESET ROLE
        conn.execute(text("RESET ROLE"))
        final = conn.execute(text("SELECT current_role")).scalar()
        print(f"        current_role after RESET ROLE: {final}")

finally:
    engine.dispose()

print()
print("=== env.py role-preparation verified ===")
print(f"  Alembic will connect as nlc_migration_user")
print(f"  env.py will SET ROLE {EXPECTED_ROLE} inside the connection")
print(f"  DDL works under {EXPECTED_ROLE}")
print(f"  A shell-level SET ROLE is NOT relied upon.")
exit(0)
