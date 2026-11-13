# NLC migration identity and restored-branch reconciliation — 13 November 2026

## Scope and safety boundary

This is a source-code and operational-readiness change only. It does not connect to production with a write-capable identity and does not execute role DDL, grants, ownership transfers, migrations, data changes, restores, or deployments.

PR #309 has merged into `main`, so `0112_runtime_acl_and_alembic_rls` is now in source control. Production remains at `0111_rule_outcome_ledger`; `0112` has not been applied. The restored Neon branch remains at `0042_dedup_key`. Do not run the migration chain against that branch until the historical-table discrepancy below has been reconciled.

## 1. Migration login and object-owner separation

### Observed production state

Read-only catalog queries against production branch `br-purple-fog-aodj8s04` (`neondb`) returned:

| Role | LOGIN | SUPERUSER | CREATEDB | CREATEROLE | INHERIT | REPLICATION | BYPASSRLS |
|---|---:|---:|---:|---:|---:|---:|---:|
| `nlc_app_role` | yes | no | no | no | no | no | no |
| `nlc_ci_audit_role` | yes | no | no | no | no | no | no |
| `nlc_migration_user` | yes | no | yes | yes | yes | no | yes |
| `neondb_owner` | yes | no | yes | yes | yes | yes | yes |

The migration login is therefore over-privileged for a narrowly controlled executor. It is not a superuser, but it has `CREATEDB`, `CREATEROLE`, `INHERIT` and `BYPASSRLS`.

The owner of both `public.rescue_audit_log` and `public.alembic_version` is `neondb_owner`, not `nlc_migration_user`. Read-only checks also returned:

- `nlc_migration_user` does not own either table or the signed-RLS helper function.
- `pg_has_role('nlc_migration_user', 'neondb_owner', 'SET')` is false.
- The observed membership row is the opposite direction: `neondb_owner` is a member of `nlc_migration_user`, granted by `cloud_admin`, with admin option true and SET/INHERIT options false. It does not allow the migration login to assume `neondb_owner`.

Consequently, simply changing Render's migration URL to `nlc_migration_user` would fail the current ownership preflight and would not give that login authority to alter migration-owned objects. Do not attempt that switch.

### Intended least-privilege architecture

Use two distinct roles:

1. `nlc_migration_user`: the LOGIN credential used by the migration runner. Required attributes: LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, NOREPLICATION, NOBYPASSRLS.
2. `nlc_migration_owner`: a NOLOGIN owner group. Required attributes: NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, NOREPLICATION, BYPASSRLS. It must own all migration-managed relations, functions and custom types in `public`, `nlc_private` and `audit`, including `alembic_version` and `rescue_audit_log`. It needs only the database/schema CREATE privileges required by the migration graph.

The only membership should be `nlc_migration_user` → `nlc_migration_owner`, with ADMIN false, INHERIT false and SET true. The login cannot inherit owner privileges; it can assume the non-login owner role only for the migration session. Do not create a reciprocal membership or reuse the current provider-managed reverse membership.

The Alembic environment in this change now:
- requires an explicit `MIGRATION_DATABASE_URL` in Render/production and does not fall back to ambiguous `DATABASE_URL`;
- requires the login session to authenticate as `nlc_migration_user`;
- validates the exact least-privilege login and non-login owner attributes;
- requires the narrow SET-only membership before executing `SET ROLE nlc_migration_owner`;
- verifies ownership of `alembic_version`, `rescue_audit_log` when present, all migration-managed relations/functions/custom types, and CREATE access to migration schemas before DDL.

This is deliberately fail-closed. Until a DBA has provisioned the owner group, transferred the migration-managed object ownership, and verified the membership and Render connection, production migrations will stop before DDL.

### DBA preparation — not executed

The following is a target contract, not an instruction to run now. A Neon-authorized DBA must first review the existing role graph, provider-managed memberships, database ownership, extension ownership, and the full object-owner inventory.

```sql
CREATE ROLE nlc_migration_owner
  NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOINHERIT NOREPLICATION BYPASSRLS;

ALTER ROLE nlc_migration_user
  LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOINHERIT NOREPLICATION NOBYPASSRLS;

GRANT nlc_migration_owner TO nlc_migration_user
  WITH ADMIN FALSE, INHERIT FALSE, SET TRUE;
```

Do not execute the above until the DBA has confirmed that the role name is unused, the membership will not create a cycle, and the existing Neon control-plane membership can remain intact. Do not use `REASSIGN OWNED BY neondb_owner` as a shortcut. Generate and review an explicit ownership-transfer inventory for each migration-managed relation, sequence, view, function, custom type and schema; exclude extension-owned objects and provider-managed objects. Verify the result on an isolated disposable branch before any production role or ownership change.

The owner group must be able to create objects in the schemas used by migrations and create required schemas in `neondb`. Configure its future-table defaults so the application role does not inherit DELETE on newly created public tables:

```sql
ALTER DEFAULT PRIVILEGES FOR ROLE nlc_migration_owner
  IN SCHEMA public
  REVOKE DELETE ON TABLES FROM nlc_app_role;
```

Do not grant CREATE, BYPASSRLS, CREATEDB or CREATEROLE to `nlc_app_role` or `nlc_ci_audit_role`.

### Render connection identity

The Render service metadata confirms service `nlc_platform`, branch `main`, auto-deploy disabled. The available service metadata does not reveal the effective database credential or the live process's `current_user`; the actual `MIGRATION_DATABASE_URL`/runtime URL mapping remains unverified. Do not print or copy connection strings into logs or chat. Verify the live process identity through a credential-safe database identity check and confirm:

- API/worker sessions use `nlc_app_role`.
- Migration sessions authenticate as `nlc_migration_user` and assume `nlc_migration_owner` only during Alembic execution.
- The deployed Render commit and database branch are the intended release targets.

## 2. Restored branch: classify missing objects by migration chronology

The restored branch `br-little-cake-aovrrz0y` is at `0042_dedup_key`. Read-only checks confirmed that the following objects are absent:

| Object | First migration in repository | Expected at 0042? | Classification |
|---|---|---:|---|
| `webhook_endpoints` | `0037_add_webhook_tables` | yes | unresolved schema drift |
| `webhook_deliveries` | `0037_add_webhook_tables` | yes | unresolved schema drift |
| `rescue_audit_log` | `0038_add_rescue_audit_log` | yes | unresolved schema drift |
| `articles_verifications` | `0048_articles_verification` | no | expected before 0048 |
| `articles_verification_events` | `0048_articles_verification` | no | expected before 0048 |
| `compliance_evaluation_runs` | `0049_evaluation_runs_and_identity_rls` | no | expected before 0049 |
| `agm_notice_evidence` | `0082_agm_share_event_provenance` | no | expected before 0082 |

This distinction matters: all seven are absent, but only the webhook and rescue-audit tables should already exist at revision 0042. The Articles, evaluation-run and AGM evidence tables are created by later migrations and should be created by the forward chain when it reaches those revisions.

The three missing pre-0042 tables are not merely empty-data cases. Their absence contradicts the applied revision marker and must be reconciled before the chain is run.

Important implementation detail: the existing historical migration `0044_webhook_schema_reconcile` does **not** fail closed when these tables are missing. It creates schema-only replacements, adds indexes, and marks the tables with `SCHEMA-ONLY RECONSTRUCTION` comments; it cannot restore historical rows. It also defines `rescue_audit_log.rescue_plan_id` with `ON DELETE RESTRICT`, whereas the original 0038 migration used `ON DELETE CASCADE`. Do not edit this already-applied historical migration. The Alembic environment itself now performs the same read-only guard before any Alembic DDL when the database is at `0042_dedup_key`, `0043_reconcile_notification_dedup_key`, or `b10c91ac6860`. This also blocks a direct `alembic upgrade` that bypasses the rehearsal script. The restore rehearsal script separately checks the three pre-0042 tables and their required columns and exits with `BLOCKED_SCHEMA_DRIFT` before invoking Alembic. It connects through `nlc_migration_user` and assumes `nlc_migration_owner`. After a successful rehearsal, the workflow verifies effective runtime DELETE grants, SELECT-only dashboard views, append-only audit tables, forced `alembic_version` RLS, all six evidence tables, and row-count preservation. No automatic override is provided: if schema-only reconstruction is formally approved after recovery attempts, it must be performed through a separately reviewed, branch-pinned reconstruction procedure before the migration chain is retried.

Do not stamp revisions, skip 0037/0038, or run the migration chain until the source schema/evidence has been reconciled and any schema-only reconstruction has been explicitly approved.

### Recovery sequence

1. Preserve the restored branch unchanged and retain its snapshot metadata and audit logs.
2. Compare its full catalog with migrations 0037 and 0038, including columns, constraints, indexes, triggers, RLS, policies, grants and ownership.
3. Search verified Neon snapshots and external object-store backups for the original table DDL and any historical rows. An empty table in current production is not proof that the 7 November snapshot contains the missing evidence.
4. If original DDL/data is found, restore it only on a new isolated recovery branch and verify row counts and relationships.
5. If no historical rows can be recovered, record the exact evidence loss and affected period and obtain an explicit authorized recovery decision. Only after that decision may a reviewed schema-only reconstruction be considered, clearly marked as reconstructed schema with zero recovered historical records. Never fabricate audit rows, webhook events, rescue events, Articles verifications or AGM notices.
6. After reconciliation, run the branch-pinned restore rehearsal on a disposable copy, from the actual `0042_dedup_key` state through the intended current head. Compare pre/post business row counts and hashes; verify all constraints, indexes, RLS, grants, signed identity and app-role negative tests.
7. Preserve the original restored branch and rehearsal evidence. Do not point Render at it and do not use it as a production cutover target until the recovery and application gates pass.

## 3. Production ACL and evidence boundaries

Production remains at `0111_rule_outcome_ledger`. Read-only ACL checks confirmed the five dashboard views still expose effective INSERT/UPDATE/DELETE privileges to `nlc_app_role`; PR #309's `0112` migration is intended to remove those privileges while retaining SELECT. The application role has no privileges on `alembic_version`; the migration owner must own it to apply the FORCE RLS change safely.

The `user_activity_logs` table is append-only under migration 0050. The current PR #309 branch has been corrected to retain archived activity-log source rows and not re-grant DELETE to `nlc_app_role`. The only confirmed application DELETE grant retained by `0112` is user-owned `webhook_endpoints` deletion.

The six production evidence tables checked by the audit remain empty. The 129 evaluation runs and their incomplete historical snapshots/hashes remain subject to PR #308's fail-closed eligibility rules. Do not reconstruct missing historical snapshots, score hashes, legal evidence or audit events from today's catalogue or application state.

## 4. Release gates

- [ ] Confirm the final PR #309 head's CI is green, including unit, integration, fresh migration and Docker runtime jobs.
- [ ] Runtime ACL integration tests prove effective privileges (including inherited/PUBLIC grants) for all five views and all public tables, not only source-text assertions.
- [ ] The migration owner role and complete object ownership are provisioned and verified on an isolated branch. PR #309's migration remains unapplied until this gate passes.
- [ ] Render's actual API and migration connection identities are independently confirmed without exposing credentials.
- [ ] The three missing pre-0042 tables are reconciled from verified evidence or covered by a formally approved evidence-loss/schema-only reconstruction decision.
- [ ] The actual restored snapshot rehearsal passes on a disposable copy; a fresh CI database migration is not a substitute.
- [ ] Production backup/recovery readiness and all release approvals are confirmed before any production migration.

**No production role, ownership, grant, schema, data, migration or deployment change is authorized by this document.**
