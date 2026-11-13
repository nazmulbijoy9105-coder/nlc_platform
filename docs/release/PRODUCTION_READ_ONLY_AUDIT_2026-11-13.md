# NLC production read-only audit — 13 November 2026

## Scope and limits

This report records read-only observations from the Neon connector and GitHub source/CI. No production SQL, DDL, role, grant, data, migration, or deployment changes were made.

The inspected Neon production target is project `rapid-bonus-26545234`, branch `br-purple-fog-aodj8s04` (`production`), database `neondb`. This is the production branch identified by Neon branch metadata and the existing runbooks. The Render service's actual `APP_DATABASE_URL` has **not** yet been independently matched to this branch; that requires confirmation of the Render workspace and service.

## Migration state

- Production `public.alembic_version`: `0111_rule_outcome_ledger`.
- Current repository migration DAG: one head, `0111_rule_outcome_ledger`, 113 revisions. The source DAG audit passed in CI run [43396002928](https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/runs/43396002928).
- The restored branch `br-little-cake-aovrrz0y`, named `nlc-legal-remediation-rehearsal-20261107`, was restored from snapshot `snap-purple-paper-ao2orhfe`. Its source snapshot timestamp is 2026-11-07 07:47:17 UTC. It remains at `0042_dedup_key`.
- CI has separately passed a **fresh disposable database** migration from `0042_dedup_key` through the current head (run [43395709224](https://github.com/nazmulbijoy9105-coder/nlc_platform), integration job). That is not a restore rehearsal of the actual Neon snapshot branch.
- The actual restored branch has not yet been migrated. The required restore rehearsal is therefore still open: run the full current chain from the restored branch's `0042_dedup_key` state through `0111_rule_outcome_ledger`, then verify schema, data preservation, indexes, constraints, RLS, and application compatibility. Do not stop at the historical `0073` target.

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

The rescue/webhook tables exist in production but their database comments identify them as schema-only reconstructions. They contain no historical rows. The restored `0042_dedup_key` branch also predates these tables. This proves that those records are not present in the inspected snapshot/production tables; it does **not** prove that no external archive exists. No S3/object-store backup inventory has been inspected, so historical evidence recovery remains unresolved. Do not create replacement rows or infer old audit events.

Evaluation integrity observations:

- 129 evaluation runs exist: 86 marked `COMPLETED` and 43 marked `NOT_RELEASED`.
- 63 older completed runs have no rule-outcome snapshot; all 43 `NOT_RELEASED` runs also have no rule-outcome snapshot.
- The latest run for each of the 23 companies has a rule-outcome snapshot. Each latest run's score, risk band and evaluation timestamp matches the corresponding company row.
- All 129 score hashes have 64-character lowercase hexadecimal form and use engine version `2.2`. This is a format check, not a recomputation of each persisted hash.
- The 74 score-history rows have 64-character hash form and an engine-version value; their hashes have not been recomputed against their complete source material.
- Missing historical rule-outcome snapshots cannot be reconstructed from today's rule catalogue. Those records must remain historically incomplete and must not become PDF-eligible through inference.

PR [#308](https://github.com/nazmulbijoy9105-coder/nlc_platform/pull/308) adds shared score-hash recomputation and fail-closed PDF/portfolio validation for runs that contain the required immutable snapshots. Its CI must pass before merge. It does not recreate missing historical evidence.

## Backup state

- The inspected project has one manual snapshot, `snap-purple-paper-ao2orhfe`, created 2026-11-07 at approximately 07:47 UTC.
- The production snapshot schedule is empty; automated Neon snapshots are not configured.
- No independent object-store archive inventory or successful external-backup restore was available during this audit.

A verified backup and a restorable snapshot are release prerequisites. Configure an automatic backup schedule and verify any external archive before further production schema changes.

## Open gates

1. Confirm the Render workspace and verify the deployed API's actual database target and runtime role without exposing credentials.
2. Execute the migration rehearsal against the actual restored branch, not merely a fresh disposable database. Preserve the pre/post row counts and schema artifact. No production migration is authorized by this report.
3. Search the external backup archive for the historical rescue/webhook evidence records. If no backup contains them, record the evidence gap as unrecoverable; do not fabricate it.
4. Configure and test scheduled backups and a separate restore path.
5. Keep statutory legal verification and product scoring release separate. Infrastructure success does not establish independent Bangladesh company-law counsel verification.
