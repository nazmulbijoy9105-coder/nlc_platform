# CI-gated production migrations

## Deployment order

The backend deployment workflow runs in this order:

1. Check that the CI-tested commit is still the current `main`.
2. Build the API image from that exact commit.
3. Run `alembic upgrade head` inside the image using the GitHub Actions secret `NLC_MIGRATION_DATABASE_URL`.
4. Trigger the Render API deployment for the same immutable commit SHA only after Alembic exits successfully.
5. Probe the Render liveness and readiness endpoints.

If the migration secret is absent, the migration identity fails validation, or Alembic fails, the workflow exits before requesting a Render deployment. A stale CI run also performs neither migration nor deployment.

## Automatic deployment opt-in

The workflow is deliberately opt-in. Successful CI on the current `main` branch does **not** by itself authorize a production migration or Render deployment.

Set this repository Actions variable:

- Name: `NLC_AUTO_DEPLOY`
- Value: `true` (The workflow checks the value in a case-sensitive shell comparison, so only exact lowercase `true` enables it)
- Location: repository **Settings → Secrets and variables → Actions → Variables → New repository variable**

If `NLC_AUTO_DEPLOY` is unset, empty, or set to anything other than the exact lowercase string `true`, the `deploy-render` job is skipped. GitHub may therefore show successful CI with no production release; this is expected while automatic deployment is not opted in. To enable automatic production releases after successful current-main CI, create or update this repository variable to `true`. To disable automatic releases, unset the variable or change its value.

This variable is a repository **variable**, not a secret. It does not replace the credentials below; the migration database secret and Render API key must also be configured for the migration and exact-commit deploy steps.

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


## Production release serialization and SHA freshness

The automatic CI-gated release workflow and the operator-controlled `production-release.yml` workflow use the same GitHub Actions concurrency group, `nlc-platform-production-release`, with `cancel-in-progress: false`. This serializes their production migration and Render operations.

The automatic workflow checks `NLC_AUTO_DEPLOY` in a shell comparison, not a GitHub expression string comparison. Only the exact lowercase value `true` enables the release; `TRUE`, `True`, whitespace variants, an empty value, and an unset variable do not.

Both workflows re-resolve `refs/heads/main` immediately before each production mutation. If current main no longer equals the workflow's immutable target SHA, the workflow stops before that mutation. The automatic workflow builds and migrates the checked-out CI-tested SHA, then submits that same SHA as Render's `commitId` and verifies the resulting deployment SHA. The controlled workflow likewise pins its Render deploy request to `github.sha` and verifies the selected deployment.

A main-branch advance after a migration but before the Render request causes the workflow to stop rather than deploy a different revision. The migration may already have applied; migration steps must therefore remain backward-compatible and the next release must reconcile the current Alembic head before deployment.


Create the Render API Actions secret:

- Name: `RENDER_API_KEY`
- Value: a Render API key authorised to inspect and deploy the configured NLC backend service.

The automatic release calls the Render deploy API with `commitId` set to the same SHA used for the migration, then polls the resulting deployment and requires that exact SHA to reach `live`. It does not use a moving-branch deploy hook.
