# NLC Platform — P0 Fix #3: Render Migration Environment Configuration

## Blocker
`MIGRATION_DATABASE_URL` is missing on Render. PR #310 fails at the migration
preflight because Alembic cannot connect with a role that has DDL privileges.

## Root Cause
The runtime `DATABASE_URL` on Render points to a connection string using the
`nlc_app_role` role. PR #309 correctly revoked `CREATE` on `public` from
`nlc_app_role`, so Alembic (which needs DDL) can no longer run migrations
using the runtime URL. A separate `MIGRATION_DATABASE_URL` using the
`nlc_migration_user` role must be configured.

## Prerequisites
1. Run `00_preflight_inspect.sql` (read-only) in the Neon SQL Editor and
   confirm you are connected as `neondb_owner`.
2. Run `01_migration_identity.sql` (v2) as `neondb_owner`. Find-replace the
   `<<SET_STRONG_PASSWORD_HERE>>` placeholder first.
3. Run `02_verify_migration_identity.sql` and confirm all 8 checks pass.
4. Capture the `nlc_migration_user` password you set in step 2.

## Steps — Render Dashboard

### 1. Open the NLC backend service
Render dashboard -> `nlc-platform` web service -> **Environment** tab.

### 2. Add the new environment variable

| Key | Value |
|-----|-------|
| `MIGRATION_DATABASE_URL` | `postgresql+asyncpg://nlc_migration_user:<PASSWORD>@<NEON_HOST>/<DB>?sslmode=require` |

- Use the same Neon host and database as `DATABASE_URL`.
- Only the username and password change (the role is `nlc_migration_user`,
  NOT `nlc_app_role`).
- If `DATABASE_URL` uses `postgresql+asyncpg://`, `MIGRATION_DATABASE_URL`
  must too (Alembic uses the same async driver).

### 3. Add a Render Secret File for the password (preferred over env var)
Render dashboard -> **Secret Files** -> Add file at `/etc/nlc/migration.env`:
```
MIGRATION_PASSWORD=<strong-password>
```
The migration preflight script reads this file and constructs the URL at
runtime, so the password is not stored in the Render env-var UI.

### 4. Update `render.yaml` (so future deploys are reproducible)

Add to the `nlc-platform` service definition:

```yaml
services:
  - type: web
    name: nlc-platform
    env: docker
    envVars:
      - key: DATABASE_URL
        sync: false          # set manually (runtime role nlc_app_role)
      - key: MIGRATION_DATABASE_URL
        sync: false          # set manually (migration role nlc_migration_user)
      - key: MIGRATION_PREFLIGHT_ENABLED
        value: "true"
      - key: MIGRATION_REQUIRE_VERIFY
        value: "true"
    secretFiles:
      - path: /etc/nlc/migration.env
```

### 5. Update the migration preflight script
The existing migration preflight (the one that failed on PR #310) must:
1. Refuse to run if `MIGRATION_DATABASE_URL` is not set.
2. Connect as `nlc_migration_user`.
3. Issue `SET ROLE nlc_migration_owner` before any DDL.
4. Run `02_verify_migration_identity.sql` as a preflight gate.
5. Run `alembic upgrade head`.
6. `RESET ROLE` and close the connection.
7. Re-run the runtime health check using `DATABASE_URL` (the `nlc_app_role` role)
   to confirm the app can read the migrated schema.

A reference preflight shell script is in `04_migration_preflight.sh`.

### 6. Re-run the failed deployment
- Render dashboard -> `nlc-platform` -> **Manual Deploy** -> Deploy latest commit.
- Watch the deploy logs. The migration preflight should now pass.
- After deploy, hit `https://nlc-platform.onrender.com/api/v1/health/ready`
  and confirm `{"status": "healthy"}`.

### 7. Verify the deployment
Run `05_verify_deployment.sh` (create from the snippet below) — it checks:
- API `/health/live` and `/health/ready` return 200.
- Current Alembic revision matches the expected head.
- Database connectivity from the runtime role (`nlc_app_role`).
- RLS policies are intact on all 16 protected tables.
- The migration log shows the most recent revision applied by
  `nlc_migration_user` (not `nlc_app_role`).

```bash
#!/usr/bin/env bash
set -euo pipefail
BASE="${RENDER_EXTERNAL_URL:-https://nlc-platform.onrender.com}"

echo "[1] /health/live";  curl -fsS "$BASE/api/v1/health/live"
echo "[2] /health/ready"; curl -fsS "$BASE/api/v1/health/ready"
echo "[3] alembic rev"
psql "$DATABASE_URL" -t -c "SELECT version_num FROM alembic_version;"
echo "[4] RLS check"
psql "$DATABASE_URL" -c "SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relname='alembic_version';"
echo "[5] runtime DDL blocked (expect ERROR)"
psql "$DATABASE_URL" -c "CREATE TABLE _t(id int);" || echo "OK: DDL blocked for nlc_app_role"
echo "DONE"
```

## Rollback
If the new preflight fails:
1. Render dashboard -> **Rollback** to the last successful deploy.
2. The runtime `DATABASE_URL` is unchanged, so the app keeps running.
3. Inspect the Neon query log to find which DDL statement failed.
4. Fix the migration script, re-run `01_migration_identity.sql` if needed,
   and redeploy.

## Do NOT
- Do NOT set `MIGRATION_DATABASE_URL` to the same value as `DATABASE_URL`
  (that defeats the entire identity separation).
- Do NOT grant `CREATE` on `public` back to `nlc_app_role` to work around this.
- Do NOT run Alembic as a Neon superuser in production.
- Do NOT commit the `nlc_migration_user` password to git, `render.yaml`,
  or any tracked file.
