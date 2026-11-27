# Governed Alembic Migration Release Contract

**Status:** Mandatory release-control specification  
**Scope:** PostgreSQL/Alembic schema and legal-registry migrations for NLC Platform  
**Authority:** This document defines evidence requirements; it does not authorize a production migration, role change, PITR cutover, or deployment.

## 1. Non-negotiable operating principles

- Migrations are forward-only by default. A downgrade is exceptional, revision-specific, reviewed for data safety, tested against a production-derived restore, and requires explicit incident-lead and authorized-DBA approval.
- The API and worker startup paths never run Alembic or seed legal rules.
- Production legal-rule and identity changes are delivered only through reviewed Alembic revisions. `scripts/seed_rules.py` is local-development/bootstrap tooling, never a production release mechanism.
- Application rollback and database recovery are separate decisions. An older application may be redeployed only after schema and data compatibility is demonstrated.
- Never stamp, skip, reorder, manually edit migration history, or mutate legal-registry rows to manufacture parity.
- Never investigate by overwriting the only production copy. PITR recovery is restored to a separate branch first.

## 2. Source and graph integrity gate

For the exact candidate commit:

1. Record the full Git commit SHA and ensure the checkout is clean.
2. Run `python scripts/audit_alembic_graph.py` and require exactly one base and one head, no duplicate revision IDs, missing parents, orphan revisions, dependency errors, or unrecognised revision files.
3. Review the full ancestry and every new revision's `revision`, `down_revision`, and `depends_on`; filenames and numeric prefixes do not establish ancestry.
4. A branch that introduces a second head must add a reviewed merge revision or rebase onto the current intended head. Never reuse a revision ID, even if its numeric prefix looks available.
5. Record SHA-256 hashes for every migration file in the candidate path and the relevant Alembic configuration.

A one-head graph audit proves source-graph consistency only. It does not prove that a database can execute the migrations or that production is at the expected revision.

## 3. Exact target and starting-state preflight

Before rehearsal, independently establish the current target facts using authorized read-only access:

- Neon project ID, database name, branch ID, branch name, parent branch ID and whether the branch is the default.
- The named, non-default backup/recovery branch from which the disposable rehearsal branch will be created.
- The actual `alembic_version` value(s), including the complete set if multiple rows exist.
- Critical schema and data preconditions for every migration in the candidate path.
- The actual runtime database target and role boundaries, without copying credentials into logs or reports.

The rehearsal must create a uniquely named disposable child of the approved backup branch and verify the returned branch's parent, non-default status, and read-write endpoint ownership before obtaining connection URIs or executing SQL. A project ID or branch ID supplied by configuration is not, by itself, proof of target identity.

For the currently supported historical rehearsal, the expected path is exactly:

`0112_runtime_acl_and_alembic_rls → … → 0128_agm001_calendar_month_definition`.

The rehearsal must assert that the newly created child begins at exactly `0112_runtime_acl_and_alembic_rls`. Any other revision set fails closed; do not silently resume from an intermediate revision or accept an already-upgraded branch as proof of the complete path. If a different baseline is to be supported, add a separately named and reviewed baseline contract and rehearsal.

## 4. Production-derived isolated rehearsal

The rehearsal must use the same migration files and commit SHA proposed for release. It must:

1. Restore from a specifically named non-default backup/recovery parent, not the production/default branch.
2. Verify the disposable child and endpoint identities before connecting.
3. Run the exact candidate migration path, without skipping or stamping revisions.
4. Capture before-images/fingerprints for protected legal-rule, finding, score, audit and other migration-sensitive data.
5. Verify every migration's expected before-state, immutable provenance/history writes, after-state, constraints and invariants.
6. Verify the final Alembic revision is the exact candidate head and exactly one revision row remains.
7. Verify schema and data parity, including columns, types, defaults, constraints, indexes, triggers, views, grants, RLS enabled/forced state and relevant policy definitions.
8. Verify tenant-boundary and score/legal-rule invariants using the intended application and audit roles.
9. Upload a machine-readable report even on failure when a report can safely be produced; a missing or incomplete report is not a pass.

A rehearsal that begins at an intermediate revision, runs a different commit, or only checks `alembic current` does not satisfy this gate.

## 5. Role-separation contract

Use three separate direct, non-pooled connections and prove identity inside PostgreSQL:

| Connection | Expected login / active role | Allowed purpose |
|---|---|---|
| Migration | `nlc_migration_user` / `nlc_migration_owner` | Controlled migration DDL and migration-managed object ownership |
| Application | `nlc_app_role` | Runtime application access only; no migration ownership or DDL authority |
| Audit | `nlc_ci_audit_role` | Read-only evidence and restricted audit-view queries |

The migration login must not be superuser, have CREATEDB/CREATEROLE, inherit owner privileges implicitly, or bypass RLS. It may assume only the reviewed non-login migration-owner role through the intended SET-only membership. The application role must not own migration-managed objects, have DDL authority, or bypass RLS. The audit role must be read-only and unable to mutate application or audit data.

The rehearsal must connect through each role, assert `session_user`, `current_user`, database and branch identity, and execute representative allowed and denied operations. Presence of a secret or a successful connection alone is insufficient.

## 6. Neon API retry and cleanup policy

HTTP 423 lock handling is bounded operational resilience, not permission to retry arbitrary failures.

- Retry only explicitly transient HTTP 423 responses (and separately documented transient transport failures).
- Honour a valid `Retry-After` header; otherwise use capped exponential backoff with jitter.
- Enforce both a maximum attempt count and a total wall-clock deadline.
- Do not retry authentication, authorization, validation, missing-resource, or other non-transient HTTP errors.
- Do not retry branch creation blindly after an ambiguous transport failure. First reconcile whether the uniquely named branch was created; never create duplicate children.
- Validate every response status and JSON shape before reading IDs.
- Clean up only the unique disposable branch created by the current run. If cleanup fails, emit a warning containing the branch identifier but no credentials.
- A lock timeout, failed cleanup, or ambiguous branch state fails the rehearsal and must be visible in the report/log.

## 7. Required evidence artifact

For each run, retain a JSON report and workflow artifact containing at least:

- Schema version of the report, UTC start/end timestamps, outcome and failure stage.
- Repository, PR number (when applicable), full commit SHA, clean-checkout status.
- SHA-256 hashes of the candidate migration files, `alembic.ini`, rehearsal script and workflow file.
- Project, database, backup parent and disposable branch identifiers/names; branch default flag and endpoint-to-branch match. Do not include connection strings, tokens, passwords or secret values.
- Actual starting revision set, expected starting revision, ordered revisions traversed and final revision set.
- Database-observed login/current roles for migration, application and audit connections.
- Before/after row counts and stable fingerprints for protected tables and legal-rule definitions.
- Required schema-object, constraint/index, trigger, RLS/policy, grant, role and application-compatibility checks with explicit booleans/results.
- Migration history/provenance checks, including before-image hashes and version transitions.
- Neon API retry counts, final cleanup status and any warnings.
- Exact commands/workflow run ID and final exit status.

The report must be bound to the candidate commit. A prior run or a green run for a different SHA is not release evidence for the current candidate.

## 8. Application compatibility and recovery contract

Each release must declare and test:

- Whether the candidate application works against the pre-migration schema (if a rolling deployment requires it).
- Whether the candidate application works against the post-migration schema.
- Whether the previously deployed application remains compatible after migration; if not, application rollback is prohibited.
- Whether a PITR-restored branch at the selected recovery point can be validated and used for a controlled cutover.
- Whether migration data transformations preserve legal-rule identity, score history, tenant isolation, evidence provenance and audit records.

Preferred recovery order:

1. Reviewed forward-fix migration.
2. PITR restore to a separate branch, validate schema/data/application compatibility, then seek controlled cutover approval.
3. Exact-revision downgrade only when its downgrade is explicitly implemented, reviewed, data-safe for the actual data shape, tested on an isolated production-derived restore, and approved by incident lead and authorized DBA.

## 9. CI and release authorization sequence

All gates are conjunctive; no gate substitutes for another:

1. Static graph audit and migration review.
2. Unit/integration tests, including migration-sensitive fixtures and identity/provenance tests.
3. Independent fresh PostgreSQL database upgrades to the candidate head.
4. Exact production-derived Neon rehearsal with the report above.
5. Security closure and dependency-license gates.
6. Application/schema compatibility checks.
7. Controlled workflow verifies required secrets and target identity before any deploy hook.
8. Execute migration, verify the resulting database state and exact head, then invoke the Render deploy hook.
9. Verify deployed commit SHA, health/readiness, critical API/UI flows, RLS/tenant isolation and worker health.

A missing secret, stale evidence artifact, unknown starting revision, multiple head, failed assertion, missing report, non-zero command exit, or mismatch between rehearsed and deploy SHA blocks release before deployment.

## 10. Production non-actions

This contract does not authorize production SQL, migration execution, Alembic stamping/downgrade, role/grant changes, PITR cutover, seed execution, or deployment. Those actions require the separate approved change/release process.
