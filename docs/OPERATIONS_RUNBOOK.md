# NLC Platform — Operations Runbook

## Quick Reference

| Resource | URL / Command |
|----------|---------------|
| Frontend | https://nlc-frontend.vercel.app |
| Backend API | https://nlc-platform.onrender.com |
| Health | GET https://nlc-platform.onrender.com/api/v1/health/live |
| Readiness | GET https://nlc-platform.onrender.com/api/v1/health/ready |
| Metrics | GET https://nlc-platform.onrender.com/metrics |
| Database | Neon PostgreSQL, project rapid-bonus-26545234 |
| Redis | Configured separately from Neon; verify the active Render/Upstash endpoint in deployment settings |
| GitHub | https://github.com/nazmulbijoy9105-coder/nlc_platform |

## Incident Response

### API is down (503 / timeout)

1. Check Render dashboard → nlc-platform → Logs and Events.
2. Check GET /api/v1/health/live and GET /api/v1/health/ready.
3. If DB is unhealthy, inspect Neon project/branch state and connection errors.
4. If Redis is unhealthy, inspect the configured Redis provider and connectivity.
5. Do not change database URLs or run migrations as a first response.
6. Verify health and record the deployed commit SHA after recovery.

### Frontend is down (500 / blank page)

1. Check Vercel project nlc-frontend → Deployments.
2. Inspect build state and deployment logs.
3. If the deployment is faulty, promote a previously verified READY deployment with a compatible backend contract.
4. Verify the production domain, login, dashboard, and API requests.

### Migration failure (Render deploy fails)

1. Capture the exact failing revision, exception, deployed SHA, and current alembic_version.
2. Inspect the migration graph and schema on an isolated Neon branch.
3. Do not edit an already-applied historical migration to hide drift.
4. Do not stamp or skip revisions to force a desired head.
5. Use a forward-only repair after review and clean/restored rehearsal.
6. Keep fail-closed preflight checks for missing historical evidence tables.

### Database recovery (data loss or schema drift)

1. Preserve the current production branch and record its revision.
2. Restore a Neon snapshot/PITR point to a separate branch.
3. Compare schema, critical row counts, constraints, indexes, grants, and RLS.
4. Recover missing evidence from a verified logical backup where possible.
5. Do not repoint Render until the isolated recovery passes the documented cutover gates.
6. See BACKUP_DISASTER_RECOVERY.md.

## Monitoring

- GET /api/v1/health/live → process liveness.
- GET /api/v1/health/ready → dependency readiness (DB + Redis + engine).
- GET /metrics → Prometheus metrics.
- Configure external uptime and error monitoring separately; do not claim alerts are active unless a live test confirms delivery.

## Backup Strategy

### Neon PITR and snapshots

Neon snapshot/PITR availability and retention depend on the current project plan and configuration. Inspect the Neon console/API rather than assuming a fixed retention period. Confirm the production branch has a non-empty snapshot schedule and record the actual retention window.

### Full PostgreSQL backup to S3

- Script: scripts/backup_to_s3.sh
- Archive verifier: scripts/verify_backup.py
- Workflow: .github/workflows/backup-neon-to-s3.yml (manual dispatch until credentials and restore drills are proven)
- Required secrets/variables are documented in BACKUP_DISASTER_RECOVERY.md.

The archive verifier checks checksum, archive TOC, and required historical table definitions. It is not a restore test. A successful isolated restore with row-count and RLS checks is required before describing backups as verified.

### Activity log archive

The Celery activity-log archival task is separate from a full PostgreSQL backup. It does not back up all tables or replace Neon PITR/S3 logical dumps.

## Deployment

### Backend (Render)

The nlc-platform service is connected to the repository's main branch. Auto-deploy is currently disabled; merging code does not deploy it. Trigger a manual deploy only after reviewing the PR, exact commit SHA, migration state, and release gates.

### Frontend (Vercel)

The nlc-frontend project deploys from GitHub. For rollback, promote a specific known-good READY production deployment and verify backend API compatibility.

## Recovery status discipline

Do not mark any recovery checklist item complete from a green build, a live DB connection, an S3 upload, or a healthy HTTP endpoint alone. Record the exact artifact, commit, database revision, branch, and test evidence supporting each claim.
