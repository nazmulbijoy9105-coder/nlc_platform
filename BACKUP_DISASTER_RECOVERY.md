# NLC Backup and Disaster Recovery Runbook

**Platform:** Render backend + Neon PostgreSQL + Vercel frontend.  
**Status:** Operational procedures are being brought into line with the deployed infrastructure. Do not use the legacy Fly.io instructions.

## 1. Non-negotiable recovery rules

1. Never run a database restore, migration, DROP, TRUNCATE, or table recreation against production as an exploratory step.
2. Restore to a separate Neon branch first. Validate schema, row counts, constraints, indexes, RLS, and application compatibility before considering a production cutover.
3. Do not treat an Alembic revision stamp as proof that the schema or historical data exists.
4. Do not recreate missing webhook or rescue-audit tables as empty tables and call that recovery. Their historical evidence may be legally or operationally material.
5. Do not use git revert as a database rollback. Application rollback and database recovery are separate procedures.
6. A backup is not verified until it has been restored into an isolated database and passed the documented integrity checks.

## 2. Current incident facts (2026-11-08)

The following are observed facts, not a statement that recovery is complete:

- Neon project: rapid-bonus-26545234; database: neondb.
- Production branch: br-purple-fog-aodj8s04; observed Alembic revision: b10c91ac6860.
- Available manual snapshot: nlc-production-pre-migration-recovery-2026-11-07, created 2026-11-07 07:47:20 UTC.
- Production snapshot schedule currently returns an empty schedule.
- Restored forensic branch: br-little-cake-aovrrz0y; observed Alembic revision: 0042_dedup_key.
- These three tables are absent from both branches: public.webhook_endpoints, public.webhook_deliveries, and public.rescue_audit_log.
- Migration 0037 creates the two webhook tables; migration 0038 creates the rescue audit table. Their absence at revision 0042 or later is schema drift.
- No S3 object listing or verified S3 backup has yet been produced in this incident. The former Fly.io S3 script is not evidence that any backup exists.

**Incident hold:** Migration 0044 intentionally stops when these historical tables are missing. Keep that fail-closed guard. Do not rerun the failing production deployment until evidence recovery or a formally approved unrecoverable-evidence decision is documented.

## 3. Neon recovery and PITR

### Inspect before restoring

1. In Neon, inspect project snapshots, branch history, and the configured snapshot schedule.
2. Record the target timestamp, snapshot ID, source branch, and current Alembic revision.
3. Create a separate recovery branch from the chosen restore point. Do not overwrite the production branch.
4. On the recovery branch, run read-only checks for:
   - Alembic revision rows;
   - the three historical evidence tables;
   - row counts for each table;
   - table columns, primary/foreign keys, indexes, triggers, policies, RLS/FORCE RLS, and grants;
   - related webhook/rescue parent tables and foreign-key relationships.
5. Compare with the migration definitions and a known-good backup. A table's existence alone does not establish that its historical rows survived.

### Cutover gate

Do not change Render's DATABASE_URL until all of the following are true:

- recovery source and restore timestamp are recorded;
- all required historical evidence is recovered or a signed, explicit loss determination is approved;
- migration graph and schema match the intended release;
- tenant isolation, signed identity, and RLS checks pass;
- application smoke tests pass against the isolated branch;
- a second operator/counsel review is recorded where legal evidence is affected;
- a fresh pre-cutover recovery point is available.

Only then may an authorized operator update the Render connection string and perform a controlled deployment. Preserve the old production branch and connection details for rollback; do not delete it during the incident.

## 4. Full logical backup to S3

The current backup script is scripts/backup_to_s3.sh. It uses pg_dump custom format against a direct Neon PostgreSQL endpoint and uploads an archive plus SHA-256 sidecar.

Required environment:
- NLC_BACKUP_DATABASE_URL: direct Neon URL using postgresql:// or postgres://, with sslmode=require, verify-ca, or verify-full. Do not use a transaction-pooler endpoint.
- S3_BACKUP_BUCKET: bucket name, not an s3:// URL.
- AWS_REGION: explicit bucket region.
- Optional S3_BACKUP_PREFIX (defaults to database).

The script requires pg_dump, pg_restore, aws, and sha256sum. It:
- creates a full custom-format logical dump, preserving database ACL statements while omitting source ownership;
- verifies the archive TOC locally;
- calculates SHA-256;
- uploads the dump and checksum with server-side encryption;
- checks the remote object's byte size and checksum metadata.

PostgreSQL logical dumps do not include cluster-level role definitions. The target Neon project must have the required roles provisioned before restoring ACLs. Keep role provisioning in reviewed infrastructure/migration configuration; do not export passwords into the backup artifact.

It does NOT prove that the database can be restored. Do not report a successful restore based only on an S3 upload or pg_restore --list.

### GitHub Actions

.github/workflows/backup-neon-to-s3.yml validates backup-tool syntax on pull requests and runs the upload only through manual dispatch. Configure:
- GitHub Actions variable AWS_REGION;
- GitHub Actions variable S3_BACKUP_BUCKET;
- GitHub Actions secret AWS_BACKUP_ROLE_ARN for an AWS IAM role trusted through GitHub OIDC;
- GitHub Actions secret NLC_BACKUP_DATABASE_URL containing a direct Neon URL.

Use least-privilege AWS permissions restricted to the designated bucket/prefix. The workflow needs object upload and HEAD/read access for the uploaded objects; large multipart uploads may also require the corresponding multipart permissions. Restrict the OIDC trust policy to this repository and the intended branch. Do not create long-lived AWS access keys if OIDC is available. Do not enable a scheduled run until a manual backup has succeeded and an isolated restore rehearsal has passed.

## 5. Archive checks versus restore tests

Run an archive check on a downloaded backup:

    python3 scripts/verify_backup.py ./nlc-postgres-YYYYMMDDTHHMMSSZ.dump

This checks the SHA-256 sidecar when present, archive TOC readability, and whether both table-definition and table-data entries exist for the three required historical evidence tables. It does not check row counts or execute a restore. A TABLE DATA entry does not prove that the table contained non-zero rows.

A proper restore drill must use a disposable Neon branch/database and a direct connection URL for that isolated target. Restore with pg_restore only after confirming the target is not production. Verify:
- all expected schemas, tables, sequences, constraints, indexes, functions, and extensions;
- row counts for critical tables, especially webhook and rescue audit evidence;
- migration revision and consistency with the archive timestamp;
- RLS enabled and forced where required, policies and grants;
- representative application reads and tenant-isolation tests.

Record archive key, checksum, source timestamp, target branch, restore duration, failures, and reviewer. Destroy the disposable target only after preserving the test report. Never use a production URL for a restore test.

## 6. Render deployment failure

The Render service nlc-platform has auto-deploy disabled. A GitHub push or merge therefore does not prove that Render deployed the new code.

1. Open Render service nlc-platform and inspect deploy history, commit SHA, pre-deploy output, and migration failure.
2. If the application image is faulty and no incompatible database migration ran, deploy the last known-good successful deploy from Render's deploy history.
3. If a migration ran or partially changed the schema, do not blindly roll back the application or downgrade Alembic. Inspect the migration state and use a forward repair or isolated database recovery plan.
4. Verify /api/v1/health/live, /api/v1/health/ready, DB identity, Redis connectivity, and key read-only application paths.
5. Record the deployed SHA and database revision.

A Git revert creates another source commit; it is not a reliable emergency deployment rollback and cannot undo database changes.

## 7. Vercel frontend rollback

1. Open the nlc-frontend Vercel project and list recent production deployments.
2. Select a previous deployment that is confirmed READY and known-good for the matching backend API contract.
3. Promote that exact deployment to production.
4. Verify the production domain, authentication, dashboard load, and API requests.
5. Record deployment ID, commit SHA, and verification result.

Do not select a deployment merely because it is older. Check its backend compatibility first.

## 8. Data export and import

Use pg_dump for a complete logical database backup. Do not use the legacy flyctl postgres connect < dump_query.sql or CSV examples as a full database export.

For selective CSV export, use psql with client-side \copy and an explicit SELECT. CSV exports are partial data extracts; they do not preserve schema, sequences, constraints, triggers, RLS policies, or all related data.

Never import customer or audit data into production without an approved change plan, a pre-import backup, conflict analysis, and post-import integrity checks.

## 9. RTO/RPO — not yet certified

| Scenario | Target | Verified status |
|---|---:|---|
| Frontend deployment rollback | To be measured | Not measured in a drill |
| Backend deployment rollback | To be measured | Not measured in a drill |
| Neon PITR recovery | To be measured | No successful incident restore recorded here |
| S3 logical backup restore | To be measured | No verified S3 archive/restore evidence yet |
| Evidence-table recovery | No target until source found | Open incident |

Do not advertise the old 1-, 2-, 5-, or 30-minute RTO claims or a 1-day RPO as achieved. Set targets only after timed restore and rollback drills.

## 10. Incident closure checklist

- [ ] A verified recovery source is identified.
- [ ] Backup checksum and archive format pass.
- [ ] Isolated restore succeeds.
- [ ] Three historical evidence tables and required rows are present, or the exact loss is formally documented and approved.
- [ ] Alembic/schema parity is proven.
- [ ] RLS, grants, signed identity, and tenant isolation pass.
- [ ] Render deployment and Vercel production compatibility are verified.
- [ ] Measured RTO/RPO and restore report are retained.
- [ ] Snapshot schedule and recurring backup process are configured and tested.
