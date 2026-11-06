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

## 1A. Human staff identity and finance separation

Human users must retain their signed UUID RLS identity. Only `SUPER_ADMIN` and `ADMIN_STAFF` may receive the shared trusted `ADMIN` service principal through the authenticated API dependency. `LEGAL_STAFF` must retain its UUID: general legal-staff policies can recognise the active database role, while finance policies must continue to deny finance access. Do not map legal staff to `ADMIN`, because the finance helper intentionally trusts that service principal for internal finance operations.

## 2. Render environment separation

Set these in the Render service before running migrations or deploying the new application:

- `DATABASE_URL`: privileged Neon migration/maintenance URL. Never use this connection for API runtime.
- `APP_DATABASE_URL`: URL for `nlc_app_role`, a non-superuser role with `BYPASSRLS=false`.
- `REQUIRE_RLS_APP_ROLE=true`. Render runtime detection also forces this guard whenever `RENDER=true`, even if `ENVIRONMENT` is omitted or misconfigured; Render services must always receive `APP_DATABASE_URL` as `nlc_app_role`.
- `NLC_RLS_HMAC_SECRET`: generate with `openssl rand -hex 32`. Use the exact same value for the migration and the application runtime. Production/Render startup now fails if this secret is missing or shorter than 32 characters. Do not paste it into chat, commits, or logs.
- Render worker and beat services must receive the same `APP_DATABASE_URL` and `NLC_RLS_HMAC_SECRET`, plus an explicit `CELERY_BROKER_URL` or `REDIS_URL`. Worker startup now enforces these requirements whenever `RENDER=true`, even if `ENVIRONMENT` is set to `development`; do not start a worker with the privileged `DATABASE_URL` fallback.

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
- No role memberships in either direction (NOINHERIT alone does not prevent `SET ROLE`).

For an authorised DBA, the attribute correction is:

```sql
ALTER ROLE nlc_app_role NOINHERIT;
ALTER ROLE nlc_ci_audit_role NOINHERIT;
```

Before migration, run this read-only membership check and require **zero rows**:

```sql
SELECT granted.rolname AS granted_role, member.rolname AS member_role
FROM pg_auth_members membership
JOIN pg_roles granted ON granted.oid = membership.roleid
JOIN pg_roles member ON member.oid = membership.member
WHERE granted.rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
   OR member.rolname IN ('nlc_app_role', 'nlc_ci_audit_role');
```

If rows are returned, stop and have the DBA assess each grant before revoking it. Do not automatically remove memberships without confirming the dependent service and access path. Migration 0050 now rejects memberships in either direction.

Create:
- nlc_app_role — set its password securely and use it only in APP_DATABASE_URL.
- nlc_ci_audit_role — set a separate password securely; use it only for the read-only production parity secret.

Do not reuse passwords, put credentials in migrations, or grant either role elevated membership. Migration 0050 performs a read-only attribute preflight and aborts with a specific error if either role is absent or unsafe. If a role already exists with incorrect attributes, correct it through the authorized Neon role-management path before deploying; do not broaden the migration credential or application role to bypass this check.

## Live production snapshot — 6 November 2026 (read-only audit)

The following observations were obtained from the live Neon production branch using read-only queries. They are release blockers until independently rechecked immediately before deployment.

### Database and rule-corpus drift

- `alembic_version` is `0042_dedup_key`; the current repository migration chain advances through `0057_merge_final_heads`. Production must be backed up and upgraded through the exact tested chain; do not skip revisions or stamp the version manually.
- Neon reports an empty snapshot schedule and no listed snapshots for the production branch. Project history retention is 21,600 seconds (six hours). This is not a verified pre-migration backup or restore rehearsal; production migration is blocked until an authorised operator creates a restorable snapshot and proves restore to a separate branch/database.
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
- The read-only inspection session was `neondb_owner` with `BYPASSRLS=true`; no separate Render application session appeared in `pg_stat_activity` at inspection time. This does not prove Render's runtime role. The app must start only with `APP_DATABASE_URL` using `nlc_app_role`, and its startup role check must pass. Production code rejects `REQUIRE_RLS_APP_ROLE=false`; do not weaken or override this guard.
- Eleven application tables currently have RLS enabled but no policy (ai_output_log, ai_prompt_templates, company_user_access, compliance_events, document_access_log, legal_rule_versions, legal_rules, quotations, sro_registry, user_activity_logs and users); migration 0050 creates scoped/staff-only policies for them. `alembic_version` is separately denied to the app role; it is not part of the tenant-table policy set. No table in the inspected inventory had FORCE ROW LEVEL SECURITY enabled. Verify every post-migration policy, FORCE RLS and negative cross-tenant tests.
- `compliance_calendar_events` currently has `company_id` but RLS is disabled. Migration 0050 includes it in the tenant-scoped table set; verify it is enabled, forced and covered by the correct company policy after upgrade.
- The live `nlc_ci_audit_role` is already `LOGIN` but currently `INHERIT`; change it to `NOINHERIT` through the authorised Neon role-management path. Do not weaken the preflight to hide this mismatch.

### 6 November 2026 live Neon production re-check (read-only)

The production Neon branch `production` (`br-purple-fog-aodj8s04`), database `neondb`, was queried read-only on 6 November 2026. The observed state is:

- `alembic_version` is `0042_dedup_key`; the expected current main migration chain is at `0057_merge_final_heads`, with PR #125 adding `0058_suppress_unreleased_rule_notifications`. Production is substantially behind the repository chain.
- `nlc_private.rls_signing_key` does not exist, confirming signed RLS identity migration 0050 has not been applied.
- `public.companies` has RLS not forced (`relforcerowsecurity=false`).
- `nlc_app_role` currently has SELECT/INSERT/UPDATE/DELETE/TRUNCATE on `companies`, `company_user_access`, `compliance_flags`, `compliance_score_history`, `notifications`, and `users`. `TRUNCATE` is not constrained by row-level policies.
- Existing permissive `PUBLIC` policies on `companies`, `compliance_flags`, `compliance_score_history`, and `notifications` trust the unsigned `current_setting('app.current_user_id') = 'ADMIN'` value. They do not verify an HMAC signature. `compliance_calendar_events` has RLS disabled. `company_user_access` and `users` have RLS enabled but no policies in this snapshot.
- Both `nlc_app_role` and `nlc_ci_audit_role` are LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION and NOBYPASSRLS, but both still have `INHERIT=true`.
- The only observed memberships involving these roles are `nlc_app_role` granted to `neondb_owner` and `nlc_ci_audit_role` granted to `neondb_owner`; both rows have `grantor_role=cloud_admin`, `admin_option=true`, `inherit_option=false`, `set_option=false`. Migration 0050 rejects any membership in either direction. The DBA must assess and remove these memberships through an authorised role-management operation before migration; do not assume that `NOINHERIT` alone satisfies the preflight.

**Consequence:** do not deploy the new API against this production database, do not start migration 0050, and do not change the score-release switch. First reconcile the production migration lineage and role topology under an approved DBA runbook, take and verify a restorable backup, then prove the post-migration role, RLS, signed identity, and tenant-isolation controls against the actual runtime connection.

### Render deployment identity and migration error
The Render `nlc_platform` service is currently on live deployment commit `9e4f99dcb3fade6510f77b555d47330e3af5b19b` (4 November 2026), triggered manually; `autoDeploy` is disabled. The latest inspected deployment remains that live revision. Merging these PRs will not automatically update production, and no deployment has been triggered from this audit.


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

### Backup and rollback policy

Before any production DDL or data migration:

1. Create a Neon snapshot/restore point for the exact `production` branch and database.
2. Verify the snapshot is complete and perform a restore rehearsal to a separate branch/database; a snapshot listing alone is not proof of recoverability.
3. Capture pre-migration row counts and checksums for companies, users, compliance flags, score history, legal rules, notifications, and financial tables (where present).
4. Keep the previous application artifact and migration logs. Do not combine a schema migration, API deployment, and rule-corpus update into one unobservable step.

**Do not use Alembic downgrade as the production rollback strategy.** Migrations `0044`, `0046`, and `0053` are now explicitly forward-only because downgrading them would disable webhook RLS, delete legal evidence/provenance, or coerce unknown AGM minutes into false values. Other security and finance migrations are also forward-only. If a migration fails after applying transactional or autocommit work, stop and diagnose; use a verified Neon restore to a separate branch for recovery planning, or apply a reviewed forward-fix. Never restore over the live branch without an approved change window and explicit confirmation.

Using a secure release runner with the privileged migration URL and the same `NLC_RLS_HMAC_SECRET`:

```bash
alembic upgrade head
alembic current
alembic heads
```

Current `main` head observed in this audit: `0057_merge_final_heads`. PR #125 adds `0058_suppress_unreleased_rule_notifications`; after that PR is merged, expected head is `0058_suppress_unreleased_rule_notifications`, with exactly one head.

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
Migration `0049_reconcile_company_profile_and_rule_registry` restores missing catalogue rows with `is_active=true` but `verification_status='PENDING'`; `is_active` is registry/parity state, not a finding of legal correctness. The public `/rules` response now exposes `verification_status`, `verified_at`, and `statutory_effective_date`. The frontend must visibly label `PENDING` and `DISPUTED`; do not present active catalogue rows as counsel-approved.

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
