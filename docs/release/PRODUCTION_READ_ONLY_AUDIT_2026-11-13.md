# NLC production read-only audit — 13 November 2026

## Scope and limits

This report records read-only observations from the Neon connector and GitHub source/CI. No production SQL, DDL, role, grant, data, migration, or deployment changes were made.

The inspected Neon production target is project `rapid-bonus-26545234`, branch `br-purple-fog-aodj8s04` (`production`), database `neondb`. This is the production branch identified by Neon branch metadata and the existing runbooks. The Render service's actual `APP_DATABASE_URL` has **not** yet been independently matched to this branch; that requires confirmation of the Render workspace and service.

## Migration state

- Production `public.alembic_version`: `0111_rule_outcome_ledger`.
- Current repository migration DAG: one head, `0111_rule_outcome_ledger`, 113 revisions. The source DAG audit passed in CI run [43396002928](https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/runs/43396002928).
- The restored branch `br-little-cake-aovrrz0y`, named `nlc-legal-remediation-rehearsal-20261107`, was restored from snapshot `snap-purple-paper-ao2orhfe`. Its source snapshot timestamp is 2026-11-07 07:47:17 UTC. It remains at `0042_dedup_key`.
- Read-only row counts on that restored branch are: 23 companies, 13 users, 12 company-access rows, 434 compliance flags, 51 score-history rows and 75 legal-rule rows. A follow-up catalog check found seven absent objects; their expected-at-0042 status is classified in the addendum below. Only the webhook and rescue-audit tables introduced by 0037/0038 should already exist at this revision.
- Current production has 23 companies, 13 users, 12 company-access rows, 549 compliance flags, 74 score-history rows, 129 evaluation runs and 86 legal-rule rows (85 active; zero rows have `verification_status='VERIFIED'`). The 7 November snapshot is therefore not a current production backup: it predates the 129-run ledger and has lower flag/history/rule row counts. Migration can create the missing schemas; it cannot recreate those later records.
- CI has separately passed a **fresh disposable database** migration from `0042_dedup_key` through the then-current head (run [43396332744](https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/runs/43396332744)). That earlier run exercised migration 0044's schema-only reconstruction behavior. PR #310 replaces that test with a fail-closed guard test: missing 0037/0038 tables must stop before 0044; the fresh baseline database remains intact for the full upgrade. The CI run is not a restore rehearsal of the actual Neon snapshot branch.
- The actual restored branch has not yet been migrated. The required restore rehearsal remains blocked until the pre-0042 webhook/rescue schema discrepancy is reconciled. Once authorized and provisioned, rehearse through the then-current head (PR #309 proposes `0112_runtime_acl_and_alembic_rls`) and verify schema, data preservation, indexes, constraints, RLS, and application compatibility. Do not run the chain merely to allow 0044 to create empty replacements.

## Runtime role and RLS observations

The following were checked directly against Neon:

- `nlc_app_role` and `nlc_ci_audit_role` are LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOINHERIT and NOBYPASSRLS.
- A direct connection as `nlc_app_role` reported `current_user = nlc_app_role`. The role has no CREATE privilege on schema `public`, and no TRUNCATE, REFERENCES or TRIGGER privilege on the inspected public tables.
- `nlc_app_role` is not a member of `neondb_owner`.
- Neon reports the provider-managed memberships `neondb_owner` → `nlc_app_role` and `neondb_owner` → `nlc_ci_audit_role`, granted by `cloud_admin`, with `ADMIN OPTION=true`, `INHERIT OPTION=false`, and `SET OPTION=false`. This exact tuple is explicitly allowed by migration `0086_runtime_role_membership_preflight` and the runtime role check. Older runbooks that require deleting these exact provider-managed memberships are superseded; do not weaken or bypass the migration preflight.
- An unsigned `ADMIN` identity with an all-zero signature was rejected by `nlc_current_user_principal()`; a direct `nlc_app_role` query with no valid signed context saw zero companies, users, and evaluation runs.
- All inspected public tenant tables have RLS enabled and forced. The only exception is `alembic_version`, which is migration metadata rather than tenant data.
- The five dashboard aggregate views inspected have `security_invoker=true`.

These are direct Neon role tests, not proof that the deployed Render process actually connects using this role. The Render connection target and runtime environment still require verification.

## Persisted evidence and evaluation observations

Observed row counts:

| Table | Rows |
|---|---:|
| `companies` | 23 |
| `users` | 13 |
| `compliance_flags` | 549 |
| `compliance_score_history` | 74 |
| `compliance_evaluation_runs` | 129 |
| `rescue_audit_log` | 0 |
| `webhook_endpoints` | 0 |
| `webhook_deliveries` | 0 |

The rescue/webhook tables exist in production but their database comments identify them as schema-only reconstructions. They contain no historical rows. On the restored `0042_dedup_key` branch, the three tables introduced by 0037/0038 are unexpectedly absent; the later Articles, evaluation-run and AGM evidence tables are not expected until their later migrations. This proves that the corresponding rows are not present in the inspected production tables; it does **not** prove that no external archive exists. No S3/object-store backup inventory has been inspected, so historical evidence recovery remains unresolved. Do not create replacement rows or infer old audit events.

Evaluation integrity observations:

- 129 evaluation runs exist: 86 marked `COMPLETED` and 43 marked `NOT_RELEASED`.
- 63 older completed runs have no rule-outcome snapshot; all 43 `NOT_RELEASED` runs also have no rule-outcome snapshot.
- The latest run for each of the 23 companies has a rule-outcome snapshot. Each latest run's score, risk band and evaluation timestamp matches the corresponding company row.
- All 129 score hashes have 64-character lowercase hexadecimal form and use engine version `2.2`. This is a format check, not a recomputation of each persisted hash.
- A read-only window-function audit compared every run's `previous_hash` with the immediately preceding `score_hash` for the same company: 129/129 direct links matched, with zero invalid genesis links and zero missing predecessor links. This is a direct-link audit, not proof that every historical hash can be recomputed.
- The immediate predecessor of each of the 23 latest company runs has no rule-outcome snapshot. Consequently, those predecessor hashes cannot be recomputed from the current persisted evidence. PR #308 verifies each latest run's own score hash and its direct pointer to the preceding run, but does not claim recursive cryptographic verification back to genesis. Historical ancestry remains partially unverifiable.
- The 74 score-history rows have 64-character hash form and an engine-version value; their hashes have not been recomputed against their complete source material.
- Missing historical rule-outcome snapshots cannot be reconstructed from today's rule catalogue. Those records must remain historically incomplete and must not become PDF-eligible through inference.

PR [#308](https://github.com/nazmulbijoy9105-coder/nlc_platform/pull/308) adds shared score-hash recomputation and fail-closed PDF/portfolio validation for runs that contain the required immutable snapshots. Its CI must pass before merge. It does not recreate missing historical evidence.

## Backup state

- The inspected project has one manual snapshot, `snap-purple-paper-ao2orhfe`, created 2026-11-07 at approximately 07:47 UTC.
- The production snapshot schedule is empty; automated Neon snapshots are not configured.
- No independent object-store archive inventory or successful external-backup restore was available during this audit.
- The repository has an S3 logical-backup workflow, but it is manual-dispatch only and requires `AWS_BACKUP_ROLE_ARN`, `AWS_REGION`, `S3_BACKUP_BUCKET`, and `NLC_BACKUP_DATABASE_URL`. No successful S3 backup run was verified.
- Neon rejected creation of a new production snapshot with `snapshots limit exceeded`; the existing 7 November recovery snapshot was preserved and not deleted.
- Neon also rejected enabling a scheduled snapshot policy because backup schedule creation is not enabled for this project. The production branch therefore remains without an automated Neon snapshot schedule.

A verified backup and a restorable snapshot are release prerequisites. Resolve the Neon plan/snapshot quota or configure and verify the S3 backup workflow before further production schema changes. Do not delete the existing recovery snapshot to make room until an independent replacement has been created and restore-tested.

## Open gates

1. Confirm the Render workspace and verify the deployed API's actual database target and runtime role without exposing credentials.
2. Execute the migration rehearsal against the actual restored branch, not merely a fresh disposable database. PR #308 adds the manual workflow `.github/workflows/neon-restored-snapshot-rehearsal.yml`; PR #310 adds a pre-migration schema guard and a scoped migration-owner contract. After the role/ownership design is provisioned and independently verified, configure `NLC_RESTORED_REHEARSAL_DATABASE_URL` to authenticate as `nlc_migration_user` (which must assume `nlc_migration_owner`) and `NLC_RESTORED_REHEARSAL_APP_DATABASE_URL` as the direct `nlc_app_role` URL, both for the exact restored branch ID `br-little-cake-aovrrz0y`. The workflow refuses any other project/branch or starting revision and now blocks before Alembic if the 0037/0038 tables or required columns are absent. After a successful approved rehearsal it checks row-count preservation, RLS, effective runtime ACLs, role grants, the private signing key boundary and unsigned ADMIN spoof rejection. It applies migrations only to the isolated restore branch; it does not touch production. Do not run it until the missing pre-0042 schema and historical evidence have been reconciled.
3. Search the external backup archive for the historical rescue/webhook evidence records and the 129 current evaluation runs. If no backup contains them, record the evidence gap as unrecoverable; do not fabricate it.
4. Configure and test scheduled backups and a separate restore path.
5. Keep statutory legal verification and product scoring release separate. Infrastructure success does not establish independent Bangladesh company-law counsel verification.


## Follow-up reconciliation addendum — 13 November 2026

A second read-only Neon catalog query against production and the pinned restore branch confirmed the following:

| Object absent on restore | First migration | Expected at revision 0042? |
|---|---|---:|
| `webhook_endpoints` | 0037 | yes — unresolved drift |
| `webhook_deliveries` | 0037 | yes — unresolved drift |
| `rescue_audit_log` | 0038 | yes — unresolved drift |
| `articles_verifications` | 0048 | no |
| `articles_verification_events` | 0048 | no |
| `compliance_evaluation_runs` | 0049 | no |
| `agm_notice_evidence` | 0082 | no |

Therefore, the absence of all seven objects is not seven independent schema-drift defects. Three are missing despite the 0042 revision marker; four are correctly absent until later migrations. The 0037/0038 tables must be reconciled before any upgrade. Historical migration 0044 creates schema-only replacements when they are absent and cannot restore rows; it also uses `ON DELETE RESTRICT` for the rescue-plan FK, while 0038 originally used `ON DELETE CASCADE`. PR #310 adds an Alembic-environment guard and a separate CI restore-guard test so direct `alembic upgrade` cannot reach 0044 with missing/incomplete pre-0042 schema.

The production migration login `nlc_migration_user` is also not a safe direct replacement for the current owner connection: it has `CREATEDB`, `CREATEROLE`, `INHERIT` and `BYPASSRLS`, while `neondb_owner` owns `public.rescue_audit_log` and `public.alembic_version`. It cannot SET ROLE to `neondb_owner`. PR #310 proposes a separate NOLOGIN `nlc_migration_owner` group, a SET-only membership, complete reviewed object ownership and an explicit Render `MIGRATION_DATABASE_URL`. This is code/runbook work only; no production role, grant, ownership, migration, data or deployment changes have been made.

The current PR #309 migration remains unapplied. It proposes to remove runtime DELETE from all public relations except authenticated user-owned webhook endpoint deletion, remove dashboard-view DML, and ENABLE + FORCE RLS on `alembic_version`. Activity-log rows remain append-only and are not deleted after S3 archival. PR #310 remains draft pending CI and DBA provisioning.
