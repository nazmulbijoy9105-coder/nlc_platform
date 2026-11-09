# NLC Production Rollback and Recovery Runbook

**Purpose:** Separate application rollback, schema repair and data recovery.  
**Safety rule:** A Git revert or application redeploy does not reverse a database migration or restore lost data.

This runbook is operational guidance, not authorization to change production. Any production action requires an incident owner, an authorized operator, a verified recovery point and an approved change plan.

## 1. Classify the incident first

Determine whether the incident is:
- application-only (bad code, compatible schema);
- schema incompatibility (application and database revisions disagree);
- data corruption or accidental deletion;
- security compromise or audit-evidence integrity failure.

Stop and preserve evidence before attempting recovery. Record the deployed application SHA, actual database target, Alembic revisions, incident time window and affected tenant/data scope. Do not place credentials or connection strings in incident notes.

## 2. Application-only rollback

1. Identify the last known-good deployment and exact immutable commit/image digest.
2. Compare that application revision's database expectations with the current production schema and data.
3. Confirm the old application does not require columns, enum values, constraints, views or data formats that have since changed.
4. If compatible, deploy the known-good application revision through the approved Render release process.
5. Verify deployment SHA, liveness, readiness, authenticated critical paths, tenant isolation, worker health and error rates.
6. Preserve logs and record the outcome.

Do not roll back application code merely because a deployment is newer. Verify compatibility first. With Render auto-deploy disabled, a merge to main does not itself deploy; retain the existing manual release boundary unless a separate policy decision changes it.

## 3. Database schema recovery

**Do not run `alembic downgrade -1` as a routine production rollback.**

Preferred sequence:
1. Stop or restrict the affected operation if continued writes could worsen the incident.
2. Capture read-only diagnostics and a verified recovery point.
3. Reproduce the failure on an isolated Neon branch restored from the relevant production point.
4. Inspect the exact Alembic graph, current revision(s), migration source, constraints, triggers, RLS policies, views and data dependencies.
5. Prefer a reviewed forward-fix migration that preserves existing data and is tested on the restored branch.
6. Rehearse the exact repair and application compatibility checks before seeking production change authorization.

A downgrade may be considered only if all of the following are true:
- the exact migration is known and its downgrade is explicitly implemented;
- the downgrade is proven data-safe for the production data shape;
- it has been exercised successfully on a production-derived isolated restore;
- no later migration or application version depends on the objects/data being removed;
- an incident lead and authorized DBA approve the exact revision and execution plan;
- pre/post verification and recovery steps are documented.

If any condition is unknown, do not downgrade. Use a forward repair or restore strategy instead.

## 4. Data recovery / Neon PITR

1. Identify the last known-good timestamp and the expected recovery point objective.
2. Restore Neon PITR into a **separate branch**; do not overwrite the production branch during investigation.
3. Verify the restored branch is accessible and inspect row counts, key relationships, audit records, evidence objects and application compatibility.
4. Compare the restore with the current production state and determine which transactions would be lost or need reconciliation.
5. Test the proposed cutover and any replay/reconciliation on an isolated environment.
6. Obtain explicit production change authorization before any cutover.
7. After an authorized cutover, verify the application runtime role, RLS, tenant isolation, audit integrity, background workers and critical user journeys.

A backup or restore point is not a verified recovery plan until it has been restored and queried. Never delete or replace the original production branch as part of the investigation.

## 5. Post-recovery checks

- Exact application SHA and database revision recorded.
- Database catalog matches the expected migration state.
- Application connects using the least-privilege runtime role, not an owner/superuser role.
- RLS is enabled and forced where required; cross-tenant negative tests pass.
- Audit/event history and evidence references are intact and traceable.
- Critical API and UI workflows pass.
- Workers, schedulers, Redis revocation and notifications behave as expected.
- Health/readiness checks and monitoring/alert delivery are verified.
- Legal score release remains disabled unless separately approved through the legal governance process.

## 6. Required incident record

Record incident ID, timeline, impact, exact commits/revisions, diagnostics, recovery point identifier, restore branch, rehearsal results, approvals, commands executed, validation evidence and follow-up actions. Never include secret values.

**No production migration, downgrade, PITR cutover, role/grant change or deployment is authorized by this document alone.**
