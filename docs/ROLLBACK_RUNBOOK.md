# NLC Production Rollback Runbook (DEP-04)

Git revert does not reverse database schema or restore data.

## App rollback (Render)
1. Manual Deploy of previous successful deploy (or known-good image digest).
2. Confirm GET /api/v1/health/live and /api/v1/health/ready.
3. With autoDeploy false, merges to main do not ship until you promote.

## Schema rollback (Alembic)
- alembic current
- alembic downgrade -1
- or: alembic downgrade <revision_id>

Every migration must implement downgrade(). Prefer expand/contract migrations.

## Data restore
Neon PITR to a timestamp before the incident, then match app revision to schema.

## Preferred order when a migration shipped
1. Stop or reduce traffic if needed
2. alembic downgrade (or PITR if data corrupted)
3. Redeploy previous app image
4. Health + smoke checks
