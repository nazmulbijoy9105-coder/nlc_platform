# Neon Production Remediation Runbook

**Status:** controlled release procedure; not authorization to change production.  
**Last read-only audit:** 7 November 2026  
**Production branch:** `br-purple-fog-aodj8s04`  
**Database:** `neondb`  
**Observed Alembic revision:** `0042_dedup_key`

This runbook records the exact blockers observed in the production Neon database and the safe order for resolving them. No production migration, role change, grant change, table recreation, data repair, or deployment is authorized by this document.

## 1. Freeze the release boundary

Do not deploy a partial PR stack. The canonical migration path is expected to end at:

- `0058_suppress_unreleased_rule_notifications` — PR #125
- `0059_finance_role_separation` and `0060_financial_billing_core` — PR #129
- `0061`–`0067` — finance ledger integrity, rescue-audit retention, verified revenue pipeline, and manual wallet-reference uniqueness — PR #130
- `0068_repair_aggregate_view_and_revenue_rls` — forward-only security repair for databases where an older `0050` or `0059` was already applied

Expected final Alembic head after the complete stack: `0068_repair_aggregate_view_and_revenue_rls`. Never stamp, skip, or manually rewrite the Alembic revision to force this value.

## 2. Create and verify a recovery point first

Before any role or schema change:

1. Create a Neon point-in-time snapshot/restore point for the production branch.
2. Restore it into an isolated Neon branch/database.
3. Verify that the restored branch can be connected to and queried.
4. Record the snapshot identifier, source branch, restore target, timestamp, and row counts for companies, users, compliance flags, score history, invoices/payments (if present), webhook evidence, and rescue audit evidence.
5. Perform the entire migration rehearsal against that isolated restored branch.

A backup that has not been restored and queried is not a verified recovery plan. Production remains frozen until the restore rehearsal succeeds.

## 3. Read-only role and membership preflight

Run as an authorized Neon administrator:

```sql
SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolinherit,
       rolreplication, rolcanlogin, rolbypassrls
FROM pg_roles
WHERE rolname IN ('nlc_app_role', 'nlc_ci_audit_role', 'neondb_owner')
ORDER BY rolname;

SELECT pg_get_userbyid(m.member) AS member_role,
       pg_get_userbyid(m.roleid) AS granted_role,
       pg_get_userbyid(m.grantor) AS grantor,
       m.admin_option, m.inherit_option, m.set_option
FROM pg_auth_members m
WHERE m.roleid IN (
    SELECT oid FROM pg_roles
    WHERE rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
)
OR m.member IN (
    SELECT oid FROM pg_roles
    WHERE rolname IN ('nlc_app_role', 'nlc_ci_audit_role')
)
ORDER BY 1, 2;
```

Observed production state:

- `nlc_app_role` and `nlc_ci_audit_role` both have `INHERIT=true`.
- `neondb_owner` is a member of both roles; grantor is `cloud_admin`; both memberships have `ADMIN OPTION=true`, `INHERIT OPTION=false`, and `SET OPTION=false`.
- `nlc_app_role` and `nlc_ci_audit_role` are LOGIN roles, non-superuser, and `BYPASSRLS=false`.
- `neondb_owner` is a privileged migration/owner role with `BYPASSRLS=true`; do not use it as the application runtime role.

### DBA-only remediation commands

Run only after the recovery point and restore rehearsal are verified, using `cloud_admin` or a Neon-authorized DBA role that can revoke the recorded memberships:

```sql
BEGIN;

ALTER ROLE nlc_app_role NOINHERIT;
ALTER ROLE nlc_ci_audit_role NOINHERIT;

REVOKE nlc_app_role FROM neondb_owner;
REVOKE nlc_ci_audit_role FROM neondb_owner;

COMMIT;
```

Do not change `neondb_owner` to NOLOGIN or remove its migration privileges as part of this step. The migration executor and application runtime are separate principals.

Re-run the role and membership queries above. The application and audit roles must have `rolinherit=false`, and the membership query must return zero rows involving either role. If the grantor/Neon control plane prevents revocation, stop and obtain the required Neon administrator action; do not bypass the migration preflight.

## 4. Reconcile missing evidence tables; do not recreate them blindly

The read-only production inventory found these tables absent even though earlier migrations should have created them:

- `public.rescue_audit_log`
- `public.webhook_endpoints`
- `public.webhook_deliveries`

These tables contain or anchor security/audit evidence. Compare the restored production snapshot with the last known-good schema and migration artifacts. Restore missing rows and DDL from a verified backup where available. If historical evidence cannot be recovered, document the exact gap, affected period, and approved recovery decision.

Do **not** create empty replacement tables or use `CREATE TABLE IF NOT EXISTS` to silence the preflight. That would make the schema appear complete while concealing missing historical evidence.

`public.compliance_evaluation_runs` is expected after migration `0049`; because production is currently at `0042`, its absence before the upgrade is not itself proof of drift. It must exist after the isolated rehearsal has applied `0049` and before `0050` proceeds.

## 5. Rehearse the full migration chain on the restored branch

On the isolated restored branch only:

1. Apply migrations from the observed `0042_dedup_key` through `0068_repair_aggregate_view_and_revenue_rls`.
2. Require exactly one Alembic head and a clean upgrade with no stamping or skipped revisions.
3. Compare pre/post row counts and key aggregates; investigate every unexplained delta.
4. Verify all expected evidence tables, constraints, indexes, triggers, and foreign keys.
5. Verify all tenant tables have RLS enabled and forced where specified.
6. Verify the five public aggregate views have `security_invoker=true`: `vw_admin_dashboard_kpis`, `vw_company_flag_summary`, `vw_risk_distribution`, `vw_upcoming_deadlines`, and `vw_revenue_pipeline`.
7. Verify `engagements` is visible only to the signed trusted `ADMIN` service principal and active `SUPER_ADMIN`/`ADMIN_STAFF` identities. Legal staff must not see engagement or revenue-pipeline rows.
8. Verify quotations: finance staff may manage them; non-staff company members may read only when their own membership has `can_view_financials=true`; legal staff must not gain access through staff status or membership.
9. Verify billing helpers: legal staff cannot read billing rows or submit payment claims even when their membership has `can_view_financials=true` and `can_edit=true`; non-staff clients need explicit financial permission, and payment submission additionally needs edit permission.
10. Run cross-tenant, forged-identity, finance-role, rejected-wallet-reference reuse, ledger reconciliation, append-only privilege, PDF reconciliation, and runtime Docker tests using the actual `nlc_app_role` connection.
11. Verify the audit credential cannot read tenant tables or assume privileged roles.

A query run as `neondb_owner` does not prove application-role RLS. The runtime proof must connect through the actual application credential and report `current_user = 'nlc_app_role'`.

## 6. Verify view and role state after rehearsal

```sql
SELECT c.relname,
       pg_get_userbyid(c.relowner) AS owner,
       c.reloptions,
       has_table_privilege('nlc_app_role', c.oid, 'SELECT') AS app_select
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public'
  AND c.relkind = 'v'
  AND c.relname IN (
      'vw_admin_dashboard_kpis',
      'vw_company_flag_summary',
      'vw_risk_distribution',
      'vw_upcoming_deadlines',
      'vw_revenue_pipeline'
  )
ORDER BY c.relname;
```

Each view must show `security_invoker=true`. The caller's base-table privileges and RLS policies must govern every view query. A view owned by `neondb_owner` must never rely on the owner's BYPASSRLS privileges for tenant-facing reads.

## 7. Separate legal release approval

Production currently has 75 active legal rules, while the repository seed catalogue contains 85 IDs; the read-only audit identified 11 missing IDs and one extra active ID. `legal_rule_versions` has zero rows. No independent counsel approval has been recorded, and `approved_rule_ids: []` must remain unchanged.

Do not auto-seed, activate, or score the missing rules to make the counts match. Reconcile every rule against the operative Bangladesh Act/Ordinance, amendment and Gazette date, commencement, applicability, evidence requirements, exceptions, and remedy. Require named, signed independent counsel approval and score-policy approval before enabling statutory score impacts or customer RED/BLACK legal alerts.

## 8. Deployment gate

Only after all three PRs are merged, the isolated production-derived rehearsal passes, and legal approval remains fail-closed as intended:

1. Record the exact merge SHA.
2. Deploy that exact SHA to Render; do not deploy an earlier PR head.
3. Verify the live service connects as `nlc_app_role`, not `neondb_owner`.
4. Verify the deployment SHA, health checks, worker/beat configuration, Redis blacklist behavior, and signed-identity round trip.
5. Re-run tenant, finance, view-security, and score-release checks against the live service.
6. Keep statutory score release disabled until the independent legal approval gate is separately satisfied.

Live bKash/Nagad/SSLCommerz checkout, provider callbacks, subscription collection, refunds, and reversals remain unimplemented. The current finance workflow is offline/manual submission and review; do not advertise live gateway collection as operational.

---

**Audit boundary:** the 7 November 2026 production checks were read-only. No production role, membership, grant, schema, data, notification, rule, migration, or deployment change was made.
