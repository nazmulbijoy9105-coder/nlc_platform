# CI product-gap map (NLC Platform)

This document maps maturity gaps to GitHub Actions introduced under
`ci/product-gap-workflows-20261127`.

## P0 — release / trust

| Gap | Workflow / mechanism |
|-----|----------------------|
| Green migration rehearsal 0112→head | Existing `production-0112-to-*` / neon rehearsal workflows (must be green on the release branch; not reimplemented here) |
| Live security closure | `security-closure-release-reminder.yml` on `main` + production-release gate |
| Single Alembic head on every PR | `alembic-single-head.yml` (also asserted inside `ci.yml`) |
| Frontend / API compatibility | `api-contract.yml` exports OpenAPI and checks required `/api/v1/*` prefixes; frontend should consume the artifact or its own `test:contracts` |
| RLS / tenant isolation as PR check | `tenant-isolation.yml` |

## P1 — production maturity

| Gap | Workflow / mechanism |
|-----|----------------------|
| Backup restore drill | `backup-restore-drill.yml` (weekly schedule + `workflow_dispatch`; live path needs Neon secrets) |
| Secret scanning | `secret-scan.yml` (Gitleaks) |
| SAST | `codeql.yml` |
| SBOM | `sbom.yml` |
| Dependency updates | `.github/dependabot.yml` |
| Worker / Celery health | `worker-health.yml` |
| License policy inventory | `license-policy.yml` |

## P2 — still manual / follow-up

| Gap | Notes |
|-----|--------|
| Cross-repo release train | Coordinate `nlc_frontend` deploy with backend OpenAPI artifact SHA |
| Synthetic user journeys | Add Playwright against staging in `nlc_frontend` or a dedicated e2e repo |
| Uptime monitor | Re-enable/tune `uptime-monitor.yml` when Render probe targets are stable |
| Load / soak tests | Not automated here; add k6/locust against staging when capacity allows |
| Full backup health UI | `disabled/backup-health-check.yml` remains disabled until secrets and owners are assigned |

## Required GitHub checks (recommended)

Mark these as required on `main`:

1. `CI` / unit-tests + integration-tests
2. `Security closure structure`
3. `Alembic single head`
4. `Tenant isolation (RLS)`
5. `API contract smoke`
6. `Secret scan`

CodeQL and license jobs may start as non-required until baselines are clean.
