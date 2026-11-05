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

## Live production snapshot — 6 November 2026 (read-only audit)

The following observations were obtained from the live Neon production branch using read-only queries. They are release blockers until independently rechecked immediately before deployment.

### Database and rule-corpus drift

- `alembic_version` is `0042_dedup_key`; the current repository migration chain advances through `0057_merge_final_heads`. Production must be backed up and upgraded through the exact tested chain; do not skip revisions or stamp the version manually.
- The live `legal_rules` table has 75 active rule IDs, while the repository seed defines 85. Missing active IDs: `BOD-001`, `BOD-002`, `BOD-003`, `ACC-001`, `ACC-002`, `ACC-003`, `DIR-007`, `DIR-008`, `DIR-010`, `MEM-001`, `INC-007`. Extra active ID: `INC-002`. Do not delete or overwrite the extra row automatically; reconcile it through the audited rule workflow.
- All 75 active database rules currently have non-zero score impact; 13 are marked BLACK. The legal approval register still has zero approved rule IDs. This database state must not be represented as counsel-approved scoring.
- All 23 companies currently have numeric cached scores (range 0–50); all 51 historical score snapshots are numeric, the latest is dated 1 October 2026, and none is marked `NOT_EVALUATED`. Fourteen of the 23 companies have a cached score that differs from their latest history score.
- Migration 0052 clears cached company scores and sets the risk band to `NOT_EVALUATED`. Migration 0051 makes history scores nullable but deliberately preserves immutable pre-release history; the API must continue returning `score: null` and `NOT_EVALUATED` until release.
- The API company/score-history serializers already redact unreleased scores. PR #125 also withholds PDF generation and automated rescue creation while `LEGAL_SCORE_RELEASED = False`; verify both after deployment. Do not issue old score-bearing PDFs or rescue plans.
- Production contains 476 queued notifications whose `notification_type` is a legal rule ID: 139 EMAIL and 337 DASHBOARD; none has been sent. These include rule-triggered alert records. PR #125 filters unapproved rule alerts from user/admin notification APIs, prevents worker delivery, adds `SUPPRESSED` status and migration 0058 suppresses the existing pending rule alerts. Non-legal deadline/payment notifications are not suppressed by the rule-ID filter.
- The notification worker is scheduled every 10 minutes. Before deploying migration 0058, pause/scale down the old worker or coordinate an atomic migration-and-restart; do not allow an old worker process to send the existing pending legal alerts.
- The production `legal_rules` schema does not yet contain the model's verification-status/evidence columns. Confirm the exact post-migration schema against the ORM before starting the API.
- `legal_rule_versions` currently has zero rows; `last_modified_by` and `last_modified_at` are unset on the live rule rows. Do not use an unversioned SQL or seed-script update to reconcile existing definitions.

- Render logs recorded three blockers: at 19:37 UTC, `NLC_RLS_HMAC_SECRET` was missing or shorter than 32 characters; at 19:43 UTC, `permission denied to alter role`; and from 19:48 UTC, `Can't locate revision identified by '0049_evaluation_runs_and_identity_rls'`.

### RLS and role findings

- A direct SQL test as `nlc_app_role` proved that setting only `app.current_user_id = 'ADMIN'` exposes 23 companies, 434 compliance flags and 51 score-history rows. This is a confirmed identity-forgery/tenant-isolation bypass in the current production policies.
- The current RLS policies trust the raw caller-settable identity GUC. Migration 0050 replaces this with an HMAC-verified principal, recreates tenant policies, and enables `FORCE ROW LEVEL SECURITY`. The exploit test must be repeated after migration and must return zero rows for an unsigned `ADMIN` GUC.
- Both `nlc_app_role` and `nlc_ci_audit_role` currently have `INHERIT=true`; migration 0050 requires `NOINHERIT`. Both roles are LOGIN and otherwise non-superuser, non-createdb, non-createrole, non-replication and NOBYPASSRLS. An authorised Neon administrator must set `NOINHERIT` before migration.
- `nlc_app_role` has grants across 37 tables, including `DELETE`, `TRUNCATE`, `REFERENCES` and `TRIGGER`. Migration 0050 revokes `TRUNCATE`, `REFERENCES`, `TRIGGER` and selected `DELETE` privileges; verify effective grants after upgrade.
- The read-only inspection session was `neondb_owner` with `BYPASSRLS=true`; no separate Render application session appeared in `pg_stat_activity` at inspection time. This does not prove Render's runtime role. The app must start only with `APP_DATABASE_URL` using `nlc_app_role`, and its startup role check must pass.
- Multiple RLS-enabled tables currently have no policies, including `company_user_access`, `legal_rules`, `legal_rule_versions`, `users`, `quotations`, `compliance_events` and activity/audit tables. No table in the inspected inventory had `FORCE ROW LEVEL SECURITY` enabled. Verify the post-migration policy inventory and negative cross-tenant tests.
- `compliance_calendar_events` currently has `company_id` but RLS is disabled. Migration 0050 includes it in the tenant-scoped table set; verify it is enabled, forced and covered by the correct company policy after upgrade.
- The live `nlc_ci_audit_role` is already `LOGIN` but currently `INHERIT`; change it to `NOINHERIT` through the authorised Neon role-management path. Do not weaken the preflight to hide this mismatch.

### Render deployment identity and migration error

- Render service `nlc_platform` is configured for branch `main` with automatic deployment disabled. Latest successful deployment observed was commit `9e4f99d`; later attempts for `51c7e6c` failed.
- Render logs recorded `permission denied to alter role` and later `Can't locate revision identified by '0049_evaluation_runs_and_identity_rls'`. The referenced migration file exists in the GitHub tree at `51c7e6c`; PR #125 CI subsequently passed the single-head and fresh-PostgreSQL upgrade jobs. The runtime artifact/database target mismatch remains unresolved. Confirm the exact deployed image and actual Render database URL before deployment; do not assume the inspected Neon branch is the same database.
- At inspection time no separate Render application session was visible in `pg_stat_activity`. The Render runtime identity must be verified after configuring `APP_DATABASE_URL`, before any migration or deployment.

### Required post-upgrade production proof

1. Query `alembic_version` and confirm the exact expected single head.
2. Connect as `nlc_app_role`; verify `rolsuper=false`, `rolbypassrls=false`, `rolcreatedb=false`, `rolcreaterole=false`, `rolreplication=false`, and `rolinherit=false`.
3. Verify the application cannot `TRUNCATE`, create triggers, or create references on tenant tables.
4. As `nlc_app_role`, set only `app.current_user_id='ADMIN'` with no signature and confirm zero rows are visible in companies, flags, score history, users and access mappings.
5. Verify signed user A can access only company A; signed user B can access only company B; forged UUIDs, stale signatures, raw ADMIN/AUTH/CATALOG sentinels and cross-tenant writes all fail.
6. Verify `compliance_calendar_events`, `company_user_access`, `users`, `legal_rules`, `legal_rule_versions`, `quotations` and every company table has the intended policy and `FORCE ROW LEVEL SECURITY`.
7. Reconcile all 85 rule IDs against the database using the audited Super Admin workflow. Preserve an immutable version row, actor, change reason and prior definition for each existing-rule change. Retire `INC-002` only after its origin and usage are established.
8. Confirm all 85 remain non-scoring / not legally approved until independent counsel approval is recorded; do not enable the release switch.
9. Confirm all existing pending rule-ID notifications are SUPPRESSED, no unapproved rule notification is returned by the user API or admin send queue, and the Celery worker suppresses any newly encountered unapproved rule alert.

**No production migration, role alteration, grant change or rule-row update has been performed by this audit.**

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

For a new/empty database, explicitly apply the insert-only seed:

```bash
python scripts/seed_rules.py --apply --verbose
```

The seeder inserts missing rows only. It never updates an existing row; if a definition differs, it reports `DRIFT` and leaves that row unchanged while allowing safe missing-row inserts to commit. Existing-rule changes must use the authenticated Super Admin `RulesService.update_rule` workflow with a named actor, mandatory `change_reason`, previous-definition snapshot and version increment. Do not use direct SQL or the seeder to modify existing legal rules.

A seed row or database row is not legal approval. Keep `approved_rule_ids: []`, `LEGAL_SCORE_RELEASED = False`, and the engine allowlist empty until independent counsel approval is recorded.

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
