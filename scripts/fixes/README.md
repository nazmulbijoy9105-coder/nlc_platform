# NLC Platform — P0 Fixes: Coordinated Package (v3)

> **2026-11-14 safety correction:** This document contains historical deployment instructions. Do not apply its Steps 1-5 to production. The migration identity script is being corrected for the supported pre-0050 state, where `nlc_private` is absent at revision `0042_dedup_key`. Use it first on the pinned isolated restore branch, run the full migration rehearsal, and obtain a separate production-release approval. Do not put migration credentials in Render's runtime `APP_DATABASE_URL`; use GitHub Actions secrets for the isolated rehearsal.

## What this is

One coordinated package — **seven files** — that unblocks the three P0
deployment blockers and reconciles the historical evaluation cohort
identified by the 13 November production audit. Not five disconnected
documents.

## The v3 corrections (expert-reviewed)

This package was reviewed against the repository's migration contract and
the 13 November production audit. Five material corrections were applied
on top of v2:

### Correction 1 — Runtime role is `nlc_app_role`, not `nlc_app`

Every SQL statement targets `nlc_app_role`. The `01_...sql` Step 9 DO block
**fails hard** with an exception if `nlc_app_role` does not exist — no
silent fallback to any other role name.

### Correction 2 — `nlc_migration_user` must NOT retain BYPASSRLS

The audit confirmed `nlc_migration_user` currently has `BYPASSRLS`. This is
a security defect: a migration role that bypasses RLS defeats row-level
security during migrations (it can see and modify rows across all tenants).

- `01_...sql` Step 2 creates the role with `NOBYPASSRLS`.
- `01_...sql` Step 2b runs `ALTER ROLE nlc_migration_user NOBYPASSRLS`
  explicitly — this revokes bypass if the role already exists with it.
- `02_...sql` Check 9 fails if `rolbypassrls` is true for `nlc_migration_user`.

### Correction 3 — The identity is a TARGET state, not current state

The audit confirms:
- `nlc_migration_owner` is currently **absent**
- `nlc_migration_user` still has `BYPASSRLS`
- `neondb_owner` still owns migration objects

So `01_...sql` is provisioning a target configuration. The preflight
(`04_...sh`) **must stop** until the identity and ownership checks pass.
It must NOT silently fall back to the existing migration login or the
runtime account.

`04_...sh` Gate 1 explicitly refuses to proceed if `MIGRATION_DATABASE_URL`
is missing or identical to `DATABASE_URL`. Gate 2 runs all 10 verification
checks and aborts on any failure. No fallback path exists in the script.

### Correction 4 — The 129-vs-106 reconciliation

The audit records **129 evaluation runs**, not 106:

| Cohort | Count | Evidence state | Classification |
|--------|-------|----------------|----------------|
| COMPLETED with full snapshots | 23 | snapshot + hash + versions | VERIFIED |
| COMPLETED missing snapshots | 63 | snapshot absent | INCOMPLETE |
| NOT_RELEASED | 43 | snapshot absent (all) | NOT_RELEASED_INCOMPLETE |
| **Total** | **129** | | |
| **Requiring preservation** | **106** | (63 + 43) | INCOMPLETE + NOT_RELEASED_INCOMPLETE |

The "106" is the subset requiring preservation-as-incomplete, NOT an
arbitrary limit. `05_...py` processes all 129 records and asserts the
counts match the audit before writing anything. If the counts do not
match, the script **refuses to write** and reports the discrepancy.

The script does NOT manufacture scores, hashes, legal verification, or
missing audit evidence. It does NOT reconstruct snapshots from today's
rule catalogue. It only writes the `integrity_status` marker.

### Correction 5 — env.py role-preparation must run inside the Alembic connection

The audit confirms `alembic/env.py` "already contains a production
role-preparation function". However, a shell-level `psql -c "SET ROLE ..."`
in the preflight script runs in a **different connection** (the psql
connection) and does NOT carry over to Alembic's SQLAlchemy connection.

The role assumption MUST happen inside `alembic/env.py`, in the Alembic
database connection, before `context.run_migrations()`. The new
`06_alembic_env_role_check.py` verifies this by:

1. Parsing `alembic/env.py` to confirm the role-preparation function exists.
2. Confirming the function is invoked in `run_migrations_online()`.
3. Opening a live SQLAlchemy connection as `nlc_migration_user`.
4. Executing the same `SET ROLE nlc_migration_owner` logic env.py would run.
5. Asserting `SELECT current_role = 'nlc_migration_owner'`.
6. Executing `CREATE TEMP TABLE` to confirm DDL works under the assumed role.

If any step fails, the preflight aborts at Gate 3 (exit code 3). The
deployment does NOT proceed.

## The seven files

```
fixes/
├── README.md                            <- this file
├── 00_preflight_inspect.sql             <- READ-ONLY, run first (11 sections)
├── 01_migration_identity.sql            <- v3, run as neondb_owner ONCE
├── 02_verify_migration_identity.sql     <- v3, 10 hard gates
├── 03_render_env.md                     <- Render dashboard + render.yaml
├── 04_migration_preflight.sh            <- v3, 5 gates, hard stop, no fallback
├── 05_reconcile_evaluations.py          <- v3, 129-cohort, 106 preserved, count assertion
├── 06_alembic_env_role_check.py         <- NEW, verifies env.py role-prep in live connection
├── reconciliation_report.json           <- generated by 05 (after run)
└── reconciliation_report.csv            <- generated by 05 (after run)
```

## Apply order (strict, no shortcuts)

```
Step 0  ->  Run 00_preflight_inspect.sql (read-only) in the Neon SQL Editor.
            Confirm:
              - You are connected as neondb_owner (Section 10)
              - nlc_app_role exists (Section 1)  [01_... will fail if not]
              - nlc_migration_user (if it exists) has BYPASSRLS = true
                (Section 1b) — this confirms the audit finding; 01_... Step 2b
                will revoke it
              - neondb_owner owns most public-schema objects (Section 3b)
                — 01_... Step 4 will transfer ownership
              - alembic_version RLS is ENABLE + FORCE (Section 7)

Step 1  ->  Open 01_migration_identity.sql in the Neon SQL Editor.
            Find-replace <<SET_STRONG_PASSWORD_HERE>> with a strong password
            (min 32 chars, e.g. `openssl rand -base64 32`).
            Execute as neondb_owner. Idempotent — safe to re-run if it fails.

Step 2  ->  Run 02_verify_migration_identity.sql.
            All 10 checks must PASS. If any fails, the script aborts at
            that check with an exception.

Step 3  ->  Run 06_alembic_env_role_check.py:
              DATABASE_URL="$MIGRATION_DATABASE_URL" \
              MIGRATION_DATABASE_URL="$MIGRATION_DATABASE_URL" \
              REPO_ROOT=/path/to/nlc_platform \
              python3 scripts/fixes/06_alembic_env_role_check.py
            This verifies env.py's role-preparation function works in a live
            SQLAlchemy connection. If it fails, fix alembic/env.py before
            proceeding.

Step 4  ->  On the Render dashboard, set MIGRATION_DATABASE_URL and add the
            secret file. See 03_render_env.md.

Step 5  ->  Wire 04_migration_preflight.sh into the Render preDeployHook.
            Commit and push to trigger the deployment.
            The preflight runs 5 gates:
              Gate 1: MIGRATION_DATABASE_URL present and distinct from DATABASE_URL
              Gate 2: 02_...sql 10 checks pass
              Gate 3: 06_...py env.py role-prep verified
              Gate 4: alembic upgrade head succeeds
              Gate 5: runtime nlc_app_role can read schema, cannot do DDL
            If any gate fails, the deployment STOPS. No fallback.

Step 6  ->  Once the deployment is healthy, run 05_reconcile_evaluations.py
            as a one-shot job (NOT in CI):
              DATABASE_URL="$DATABASE_URL" python3 scripts/fixes/05_reconcile_evaluations.py
            The script:
              - reads all 129 records
              - classifies each (VERIFIED / INCOMPLETE / NOT_RELEASED_INCOMPLETE / BROKEN_CHAIN)
              - asserts counts match the audit (129 total, 23 verified, 106 preserved)
              - only writes integrity_status if the assertion passes
              - outputs reconciliation_report.json + .csv
            Review the report with counsel before any further action.

Step 7  ->  Address the empty evidence tables identified in the report.
            Each empty table corresponds to an ingestion pipeline gap.
            Do NOT insert fake evidence — build the ingestion.
```

## What this package does NOT do

- Does NOT grant `CREATE` on `public` back to `nlc_app_role`.
- Does NOT run Alembic as a Neon superuser.
- Does NOT retain `BYPASSRLS` on `nlc_migration_user`.
- Does NOT fall back to the existing migration login or runtime account
  if the identity verification fails.
- Does NOT rely on a shell-level `SET ROLE` to persist into Alembic's
  SQLAlchemy connection.
- Does NOT fabricate or auto-reconstruct the 106 historical evaluations.
- Does NOT reconstruct snapshots from today's rule catalogue.
- Does NOT manufacture scores, hashes, legal verification, or audit evidence.
- Does NOT insert fake rows into the six empty evidence tables.
- Does NOT flip `LEGAL_SCORE_RELEASED` to `True` — that requires counsel
  sign-off, which is a separate P0 workstream (see the gap report).

## Verification after applying

After Steps 0-5 succeed:

```bash
# 1. Deployment is up
curl -fsS https://nlc-platform.onrender.com/api/v1/health/live
curl -fsS https://nlc-platform.onrender.com/api/v1/health/ready

# 2. Alembic revision
psql "$DATABASE_URL" -t -c "SELECT version_num FROM alembic_version;"

# 3. Runtime role CANNOT do DDL (expect ERROR: permission denied)
psql "$DATABASE_URL" -c "CREATE TABLE _test_ddl_block (id int);"

# 4. Migration role CAN do DDL (after SET ROLE — inside Alembic's connection)
psql "$MIGRATION_DATABASE_URL" -c \
  "SET ROLE nlc_migration_owner; CREATE TABLE _test_ddl_ok (id int); DROP TABLE _test_ddl_ok; RESET ROLE;"

# 5. RLS intact on alembic_version
psql "$DATABASE_URL" -c "
  SELECT relname, relrowsecurity, relforcerowsecurity
  FROM pg_class WHERE relname = 'alembic_version';"
# Expected: alembic_version | t | t

# 6. All public tables owned by nlc_migration_owner
psql "$DATABASE_URL" -c "
  SELECT relname, pg_get_userbyid(relowner) AS owner
  FROM pg_class c
  JOIN pg_namespace n ON n.oid = c.relnamespace
  WHERE n.nspname = 'public' AND relkind = 'r'
  ORDER BY relname;"
# Expected: every row shows owner = nlc_migration_owner

# 7. nlc_migration_user does NOT have BYPASSRLS
psql "$DATABASE_URL" -c "
  SELECT rolname, rolbypassrls FROM pg_roles
  WHERE rolname = 'nlc_migration_user';"
# Expected: nlc_migration_user | f

# 8. After 05_...py runs, verify the 129/106 cohort
psql "$DATABASE_URL" -c "
  SELECT integrity_status, COUNT(*)
  FROM compliance_score_history
  GROUP BY integrity_status
  ORDER BY integrity_status;"
# Expected:
#   BROKEN_CHAIN            | (some)
#   INCOMPLETE              | 63
#   NOT_RELEASED_INCOMPLETE | 43
#   VERIFIED                | 23
# (counts may vary slightly if BROKEN_CHAIN records exist in either sub-cohort)
```

## Rollback

If the new preflight fails and you need to restore the previous state:

```sql
-- 1. Transfer ownership back to neondb_owner
DO $$
DECLARE obj record;
BEGIN
  FOR obj IN
    SELECT n.nspname, c.relname
    FROM pg_class c
    JOIN pg_namespace n ON n.oid = c.relnamespace
    WHERE n.nspname = 'public' AND c.relkind IN ('r','S','v','m')
  LOOP
    EXECUTE format('ALTER TABLE %I.%I OWNER TO neondb_owner', obj.nspname, obj.relname);
  END LOOP;
END $$;

-- 2. Re-grant CREATE to nlc_app_role (only if you want the old behaviour back)
GRANT CREATE ON SCHEMA public TO nlc_app_role;

-- 3. Drop the new roles
DROP ROLE nlc_migration_user;
DROP ROLE nlc_migration_owner;

-- 4. The integrity_status columns on compliance_score_history are harmless;
--    leave them or drop them:
ALTER TABLE compliance_score_history
  DROP COLUMN IF EXISTS integrity_status,
  DROP COLUMN IF EXISTS integrity_audited_at,
  DROP COLUMN IF EXISTS integrity_missing_fields,
  DROP COLUMN IF EXISTS integrity_classification_source;
```

## After these fixes

The three deployment BLOCKERS are resolved. The 106-record cohort is
preserved as incomplete with an explicit audit trail. The remaining P0
workstreams from the gap report are:

- **L1/L2/L3**: 85-rule counsel sign-off (longest lead time — start now)
- **C1/C3**: bKash + SSLCommerz + NBR invoicing
- **S1**: verify_tenant_isolation.py as a CI gate
- **O3**: staging environment
- **O5**: SAST + dependency scan + container scan in CI

See `NLC_Gap_Analysis_Commercial_Readiness.docx` for the full roadmap.
