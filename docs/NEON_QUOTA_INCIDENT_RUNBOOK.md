# Neon production quota exhaustion runbook

## Purpose

Recover database availability safely when Neon suspends a project after a monthly Free-plan quota is exhausted. This is an infrastructure incident, not a reason to weaken application startup checks, readiness probes, tenant RLS, or release controls.

## Detection

Treat any of the following as a provider-quota incident until disproven:

- Neon connection failures report that the account or project exceeded a quota.
- Render logs show `db_connectivity_failed` followed by `Application startup failed. Exiting.`.
- Render records repeated non-zero process exits while the database endpoint refuses new connections.
- Neon project usage reaches the applicable monthly compute or public network transfer allowance.

Capture the incident timestamp, affected Neon project/branch, Render service, current deployed commit SHA, database revision (if independently available), and usage counters. Never include connection strings, passwords, or tokens in incident notes.

## Safe recovery sequence

1. **Confirm the target.** Verify the Render service's configured database endpoint by its non-secret project/branch identity. Do not print or copy secret environment-variable values into logs or tickets.
2. **Inspect usage.** In Neon, inspect the affected project's current billing period, compute usage, public network transfer, storage, and quota reset timestamp. Do not assume an account-wide limit when the allowance is project-scoped.
3. **Restore entitlement.** For a customer-facing production system, move the production project to an appropriate paid Neon plan and confirm that the project is no longer quota-suspended. Waiting for the monthly reset is an emergency temporary option only when the business owner explicitly accepts the outage.
4. **Verify database access read-only.** Confirm the production branch is ready, then run a read-only connectivity check using the runtime role. Confirm the role identity and least-privilege posture. Do not run migrations as part of quota recovery.
5. **Verify application health.** Only after database access is restored, verify Render liveness and readiness, then authenticated read-only application paths and tenant isolation.
6. **Reconcile usage drivers.** Review query volume, repeated polling, over-fetch, oversized response payloads, background jobs, backup/replication egress, and branch activity. Reduce avoidable traffic without weakening legal evidence, audit logging, or tenant isolation.
7. **Record closure.** Capture provider plan/entitlement confirmation, usage before and after, exact Render SHA, health results, database revision, and incident owner approval.

## Prohibited shortcuts

- Do not bypass the database startup check or report readiness while the production database is unavailable.
- Do not point Render at a development, rehearsal, backup, or newly-created database to make health checks green.
- Do not delete production data, branches, backups, or audit records to reclaim quota without a separately approved retention and recovery plan.
- Do not run Alembic, seed rules, rotate credentials, or deploy application code as an attempted quota fix.
- Do not treat a successful container build, liveness response, or restored ephemeral backup as proof that production is recovered.

## NLC-specific observed incident (2026-11-27)

The Render service `nlc_platform` emitted a PostgreSQL provider error stating that the Neon account or project had exceeded quota, followed by application startup failure. The connected Neon organization was on the Free plan. The NLC project usage record showed approximately 5.55 GB of public network transfer for the November 1–December 1 billing period, above the Free-plan allowance of 5 GB per project per month. Reported compute usage was about 57.2 CU-hours, below the documented 100 CU-hour Free allowance; reported logical size was about 70.5 MB, below the 1 GB project storage allowance. This points to public network transfer exhaustion as the likely trigger. Neon project usage and the provider's quota error are the authoritative evidence; re-check both before closing the incident.

The provider's Free-plan quota resets at the start of the next billing period. For commercial production, use a paid plan rather than relying on a monthly reset. Do not mark the incident resolved until the live project accepts connections and Render readiness and application-level checks pass.

## References

- Neon Free-plan limits and quota behavior: https://neon.com/docs/introduction/plans
- Neon Free-plan limits FAQ: https://neon.com/docs/introduction/free-plan-limits-and-quotas
