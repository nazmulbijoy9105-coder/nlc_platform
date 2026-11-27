# CI-gated production migrations

## Deployment order

The backend deployment workflow runs in this order:

1. Check that the CI-tested commit is still the current `main`.
2. Build the API image from that exact commit.
3. Re-check that the release SHA is still current `main` immediately before the production database mutation.
4. Run `alembic upgrade head` inside the image built from that exact commit, using the GitHub Actions secret `NLC_MIGRATION_DATABASE_URL`.
5. Re-check freshness again after migration and immediately before requesting the Render deployment.
6. Request a Render deployment with `commitId` explicitly pinned to the same SHA used to build the migration image; verify the resulting deployment reports that exact SHA and reaches `live`.
7. Probe the Render liveness and readiness endpoints.

The initial freshness check is only an early rejection of stale CI runs; it is not reused as authorization for later release mutations. If `main` advances during image build or migration, the immediately-following freshness gate fails closed: no database migration is started if the advance is detected before Alembic, and no Render deployment is requested if the advance is detected after migration. The Render API request must carry the immutable CI-tested SHA as `commitId`; it must never deploy the moving `main` branch or rely on a deploy hook that resolves the branch at trigger time.

The Render deployment is therefore pinned to the same source SHA as the migration image. If `main` advances after the final freshness check but before Render accepts the request, the request is still pinned to the migrated SHA rather than silently switching to the newer branch head. The subsequent deployment verification rejects any deployment whose reported commit differs from that SHA.

If the migration secret is absent, the migration identity fails validation, Alembic fails, a freshness re-check fails, or Render does not accept and deploy the exact requested SHA, the workflow fails closed. A stale CI run does not authorize a migration or deployment.

## Automatic deployment opt-in

The workflow is deliberately opt-in. Successful CI on the current `main` branch does **not** by itself authorize a production migration or Render deployment.

Set this repository Actions variable:

- Name: `NLC_AUTO_DEPLOY`
- Value: `true` (GitHub compares strings case-insensitively, so `TRUE` or `True` also enables it)
- Location: repository **Settings → Secrets and variables → Actions → Variables → New repository variable**

If `NLC_AUTO_DEPLOY` is unset, empty, or set to anything other than `true` in any letter case, the `deploy-render` job is skipped. GitHub may therefore show successful CI with no production release; this is expected while automatic deployment is not opted in. To enable automatic production releases after successful current-main CI, create or update this repository variable to `true`. To disable automatic releases, unset the variable or change its value.

This variable is a repository **variable**, not a secret. It does not replace the credentials below; both required secrets must also be configured for the migration and Render deployment steps.

## Required GitHub Actions secret

Create the repository Actions secret:

- Name: `NLC_MIGRATION_DATABASE_URL`
- Value: the TLS-enabled PostgreSQL connection URL for the dedicated `nlc_migration_user` login.

Do not put this credential in the Docker image, Dockerfile, repository, or Render API environment. The API container starts Uvicorn directly and does not receive the migration credential.

The database must first be provisioned to satisfy the production role contract enforced by `alembic/env.py`:

- `nlc_migration_user`: LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, NOREPLICATION, NOBYPASSRLS.
- `nlc_migration_owner`: NOLOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOINHERIT, NOREPLICATION, BYPASSRLS.
- The login has only a non-admin, non-inheriting SET ROLE membership in the owner role.
- The owner role owns every migration-managed relation, function, custom type and the Alembic version table, and has only the reviewed database/schema creation privileges required by the migration chain.
- No PUBLIC or runtime-role default DELETE grants are present.

Do not add the Actions secret until the DBA has provisioned and verified that contract. The currently observed production state does not yet meet it: `nlc_migration_owner` is absent and `nlc_migration_user` still has BYPASSRLS. The deployment gate is intentionally expected to fail closed until that is corrected.

## Operational note

Migrations run before the new API version is deployed, so schema changes must remain backward-compatible with the currently live application during the deployment window. Use expand/contract migrations for changes that would otherwise break the old version. Do not use this workflow to restore or reconstruct missing historical evidence.
