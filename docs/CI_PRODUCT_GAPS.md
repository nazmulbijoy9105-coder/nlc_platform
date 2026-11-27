# CI product-gap map (NLC Platform)

This document maps the CI controls introduced by
`ci/product-gap-workflows-20261127` to the product risks they are intended
to detect. A workflow passing is evidence only for the checks it actually runs.

## P0 — release / trust

| Gap | Workflow / mechanism |
|-----|----------------------|
| Green migration rehearsal 0112→head | Existing production Neon rehearsal workflows; these remain a separate release gate and must pass on the exact release SHA |
| Live security closure | `security-closure-release-reminder.yml` on `main` + controlled production-release gate |
| Single Alembic head and DAG audit | `alembic-single-head.yml` on every PR and push to `main` |
| Frontend / API compatibility | `api-contract.yml` exports OpenAPI and validates exact client operations, successful JSON response schemas and path-segment prefixes |
| Database tenant isolation | `tenant-isolation.yml` provisions isolated PostgreSQL roles and runs database-backed cross-tenant, RLS and privilege-boundary integration tests |

## P1 — production maturity

| Gap | Workflow / mechanism |
|-----|----------------------|
| Backup recovery | `backup-restore-drill.yml` creates a backup from the configured read-only/direct source URL, verifies its archive/checksum and restores that same archive into an ephemeral PostgreSQL service; optional pinned Neon migration rehearsal uses separate restored-branch URLs |
| Secret scanning | `secret-scan.yml` (Gitleaks) |
| SAST | `codeql.yml` |
| SBOM | `sbom.yml` generates CycloneDX from the declared application requirements file, not the CI environment |
| Dependency updates | `.github/dependabot.yml` |
| Worker / Celery health | `worker-health.yml` asserts the named critical beat tasks and their task targets |
| License policy | `license-policy.yml` uses an explicit allowlist; unknown/unapproved metadata fails closed. PSFL remains unapproved until the project owner records a decision |

## Protected recovery credentials

The backup workflow is restricted in YAML to `refs/heads/main`, checks out
`main` explicitly, and uses the `production` environment. Configure that
GitHub environment outside this repository to allow deployments from `main`
only and require an authorised reviewer. Do not store Neon or backup database
credentials as unrestricted repository secrets. The backup source URL must be
a direct TLS PostgreSQL connection suitable for `pg_dump`; the disposable
restore target is created by the workflow and is not production.

## P2 — still manual / follow-up

| Gap | Notes |
|-----|--------|
| Cross-repo release train | Coordinate `nlc_frontend` deploy with the exact backend OpenAPI artifact SHA |
| Synthetic user journeys | Add Playwright against staging in `nlc_frontend` or a dedicated e2e repo |
| Uptime monitor | Re-enable/tune `uptime-monitor.yml` when Render probe targets are stable |
| Load / soak tests | Not automated here; add k6/locust against staging when capacity allows |
| Full backup health UI | `disabled/backup-health-check.yml` remains disabled until owners and secrets are assigned |
| Production restore/migration equivalence | An ephemeral PostgreSQL restore proves the archive is restorable; it does not replace the separate isolated Neon 0112→current-head rehearsal or production release approvals |

## Recommended required GitHub checks

Mark these as required on `main` after the baseline is green:

1. `CI` / unit-tests + integration-tests
2. `Security closure structure`
3. `Alembic single head`
4. `Tenant isolation (PostgreSQL RLS)`
5. `API contract smoke`
6. `Secret scan`
7. `Dependency license policy`

CodeQL and SBOM can begin as non-required checks until their baselines and
artifact consumers are confirmed.
