# CI-gated production migrations

## Deployment order

The backend deployment workflow runs in this order:

1. Check that the CI-tested commit is still the current `main`.
2. Build the API image from that exact commit.
3. Run `alembic upgrade head` inside the image using the GitHub Actions secret `NLC_MIGRATION_DATABASE_URL`.
4. Trigger the Render deploy hook only after Alembic exits successfully.
5. Probe the Render liveness and readiness endpoints.

If the migration secret is absent, the migration identity fails validation, or Alembic fails, the workflow exits before calling the Render deploy hook. A stale CI run also performs neither migration nor deployment.

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
