# NLC production score-gate release runbook

**Release posture:** statutory scoring remains disabled until each rule has individual counsel approval. A successful deployment is not legal approval.

## 1. Preconditions

Do not merge/deploy until the latest backend and frontend CI checks pass, including:
- unit tests;
- integration and RLS tests;
- exactly one Alembic head;
- clean database upgrade through the current head;
- Docker runtime smoke (including writable Fontconfig cache);
- engine/seed inventory parity and the fail-closed legal approval check.

The current backend release branch keeps:
- `LEGAL_SCORE_RELEASED = False`;
- `VERIFIED_RULE_IDS = frozenset()`;
- every rule in `REVIEW_REQUIRED` and `score_eligible: false`.

Do not change these until counsel approval is recorded rule-by-rule.

## 2. Render environment separation

Set these in the Render service before running migrations or deploying the new application:

- `DATABASE_URL`: privileged Neon migration/maintenance URL. Never use this connection for API runtime.
- `APP_DATABASE_URL`: URL for `nlc_app_role`, a non-superuser role with `BYPASSRLS=false`.
- `REQUIRE_RLS_APP_ROLE=true`.
- `NLC_RLS_HMAC_SECRET`: generate with `openssl rand -hex 32`. Use the exact same value for the migration and the application runtime. Do not paste it into chat, commits, or logs.

The runtime engine uses `APP_DATABASE_URL`; Alembic uses `DATABASE_URL`. The application refuses to start in production without `APP_DATABASE_URL`.

## 3. Provision database roles (one-time, outside Alembic)

Before migration 0050, provision both cluster roles through the Neon project role-management interface or an authorized database administrator session. The migration deliberately does not create, alter, reset passwords for, or grant membership in roles.

Required attributes for both roles:

- LOGIN
- NOSUPERUSER
- NOCREATEDB
- NOCREATEROLE
- NOINHERIT
- NOREPLICATION
- NOBYPASSRLS

Create:
- nlc_app_role — set its password securely and use it only in APP_DATABASE_URL.
- nlc_ci_audit_role — set a separate password securely; use it only for the read-only production parity secret.

Do not reuse passwords, put credentials in migrations, or grant either role elevated membership. Migration 0050 performs a read-only attribute preflight and aborts with a specific error if either role is absent or unsafe. If a role already exists with incorrect attributes, correct it through the authorized Neon role-management path before deploying; do not broaden the migration credential or application role to bypass this check.

## 4. Apply database migrations

Using a secure release runner with the privileged migration URL and the same `NLC_RLS_HMAC_SECRET`:

```bash
alembic upgrade head
alembic current
alembic heads
```

Expected current head: `0052_invalidate_unreleased_legacy_scores`, with exactly one head.

Migration 0052 clears only current company-level score/risk/exposure state and disables score-triggered rescue state. It preserves the immutable monthly history rows. API responses independently suppress legacy history scores while release is disabled.

Do not run migrations through the runtime `nlc_app_role` connection.

## 5. Synchronise the production rule catalogue

The production database previously had 75 active rules while the canonical engine/seed inventory contains 85. The live parity audit will fail until the catalogue is synchronised.

First run a dry run with the privileged `DATABASE_URL`:

```bash
python scripts/seed_rules.py
```

Review the planned changes, then explicitly apply:

```bash
python scripts/seed_rules.py --apply --verbose
```

This upserts rule metadata by `rule_id`. It does **not** approve rules or enable statutory scoring. Keep the fail-closed engine allowlist empty.

## 6. Deploy backend and refresh evaluation snapshots

The Render service has automatic deploy disabled. After the backend PR is reviewed and merged, manually deploy the exact merged `main` commit.

After the service starts:
1. Verify the deployed commit SHA in Render.
2. Verify the runtime database role through the authenticated `/api/v1/admin/security/rls-status` endpoint.
3. Verify `current_user = nlc_app_role`, `rolsuper=false`, and `rolbypassrls=false`.
4. Verify the database is at the single expected Alembic head.
5. Re-evaluate each active company through the authenticated administrative evaluation workflow so a fresh `compliance_evaluation_runs` record is created. With release disabled, these records must be `NOT_RELEASED`, with null scores and `NOT_EVALUATED` bands. Do not expect a legal score.

PDF generation must remain withheld when there is no completed, reconciled, released evaluation snapshot.

## 7. Configure read-only production parity

Migration 0050 grants `nlc_ci_audit_role` read-only access to `audit.active_legal_rule_ids`; the role itself must already have been provisioned out-of-band. After the migration:

1. Generate a separate password (for example, `openssl rand -hex 32`).
2. Set it for `nlc_ci_audit_role` in the Neon SQL console using the privileged owner session.
3. Build a PostgreSQL connection URL for that role only.
4. Add it as the GitHub Actions repository secret named `NLC_PRODUCTION_DATABASE_URL`.

Never use `DATABASE_URL` or `APP_DATABASE_URL` as this secret. The CI audit credential must not be able to modify production data.

Then run the GitHub Actions workflow **Production Rule Parity**. It compares the live database view, public API catalogue, engine and seed. All four inventories must match.

## 8. Frontend and final security verification

After backend deployment and API verification:
- merge/deploy the frontend score-visibility PR;
- verify the Vercel production deployment commit;
- verify the Vercel API base URL points to the intended Render service;
- test `NOT_EVALUATED`, null score, released score and historical score states;
- run cross-tenant access, forged-GUC, signed-identity, staff/admin authorization and RLS tests;
- confirm PDFs cannot be generated from stale or inconsistent snapshots.

## 9. Release authority

Statutory scoring stays disabled until:
- every rule has an individually verified legal source, applicability, effective date and counsel approval;
- the approved rule IDs are explicitly entered into the approval register and engine allowlist;
- legal and technical regression tests pass;
- production DB/API/engine/seed parity passes;
- human oversight and audit evidence are verified.

A green CI run, a successful deployment, or an active database rule is not a substitute for counsel approval.
