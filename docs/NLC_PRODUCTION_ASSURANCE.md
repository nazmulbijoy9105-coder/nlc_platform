# NLC production assurance

NLC is a **legal-compliance scoring product**. Technical deploy success is not
sufficient. Two independent chains must both pass on the **same commit SHA**
before a published RJSC score is trustworthy. Both controlled Render release
workflows wait for a successful push-triggered legal-engine assurance run for
the exact release SHA before any production migration or deployment step:

1. **Infrastructure release chain** — CI, migrations, deploy, backups, ops.
2. **Legal-engine assurance chain** — catalogue, scope, provenance, publication.

## HOLD criteria

Do **not** declare production-ready until:

- [ ] Green CI on the exact release SHA (lint, unit, integration, docker smoke)
- [ ] Successful isolated Neon migration rehearsal **0112 → repository head**
- [ ] Single authoritative production release path (no competing auto-migrate)
- [ ] Live security closure (all findings CLOSED + live dependency audit)
- [ ] Legal-engine P0 gates green (catalogue, RJSC scope, provenance, publication)
- [ ] Post-deploy tenant smoke + rule parity evidence retained

## Target architecture (one assurance chain)

```text
Pull request validation
  → lint, unit/integration, SAST/secrets/deps, single Alembic head,
    RLS/tenant isolation, legal-engine static gates

Cross-repository compatibility
  → OpenAPI contract, frontend compatibility, client drift, browser E2E

Migration rehearsal (protected / not a casual PR check)
  → restore known baseline → exact head → schema, roles, grants, data

Release authorization (protected production environment)
  → live security closure, human approval, exact SHA, migration evidence

Post-deployment verification
  → tenant smoke, 85-rule parity (live), score provenance, scope isolation,
    withheld-score behaviour

Continuous production assurance
  → backup/restore drills, worker/queue monitoring, synthetic journeys,
    uptime alerts, incident escalation
```

## P0 — release-blocking / trust-blocking

| Control | Why it matters | Required evidence | Status in repo |
|---------|----------------|-------------------|----------------|
| 85-rule catalogue integrity | Deploy is meaningless if rules diverge | Exact parity source ↔ DB ↔ evaluator ↔ API | Static PR gate; live parity on release/post-deploy |
| RJSC scope isolation | Non-RJSC must not move RJSC score/band | Inject 26 OUT_OF_SCOPE without score/hash change | Unit suite + legal-engine workflow |
| Score provenance & reproducibility | Reconstruct any published score | Hash, rule versions, evidence, snapshot, engine | Evaluation integrity tests |
| Fail-closed publication | No misleading published score | Withheld / NOT_EVALUATED under blockers | Score visibility tests |
| Human approval & override audit | AI must not silently become legal decision | Actor, time, prior rec, override reason, immutable log | Partial — extend CI |
| AuthZ matrix (role × endpoint × tenant) | Tenant isolation ≠ correct staff/director/admin powers | Positive + negative matrix tests | Partial (company-access / route tests) |
| Migration rollback/recovery policy | Tech success ≠ safe operate | Forward-fix, PITR, documented recovery | Docs + rehearsal; dual deploy path still a risk |

## P1 — production maturity

| Control | Why it matters |
|---------|----------------|
| Auth security testing | Session expiry, refresh rotation, lockout, privilege escalation |
| Rate limiting / abuse protection | Login, evaluation, upload, expensive AI |
| File/document security | Type/size limits, malware, storage ACLs, download auth |
| PII / sensitive-data controls | Retention, deletion, encryption, access log, redaction |
| Application observability | Structured logs, correlation IDs, traces API+workers |
| Alerting / escalation | Failed evaluations, queue backlog, DB pool, auth storms |
| Queue reliability | Celery retries, idempotency, DLQ, worker restart |
| Email/WhatsApp delivery assurance | Failures, retries, duplicates, message audit |
| DB connection resilience | Pool exhaustion, transient disconnect, txn failure |
| Security incident response | Credential rotation, containment, evidence, recovery |

## P2 — product / commercial readiness

| Control | Why it matters |
|---------|----------------|
| E2E legal workflow | Registration → profile → evaluate → review → approve → file → calendar |
| Frontend a11y/usability | Dashboards, forms, risk indicators, documents |
| API docs & version lifecycle | Breaking-change and deprecation policy |
| Tenant onboard/offboard | Setup, transfer, suspend, export, close |
| Billing/entitlement enforcement | Limits and suspended accounts cannot bypass API |
| Product analytics | Completion, failures, approval delay, usage |
| Legal content update process | Legislation changes reviewed, versioned, approved |
| Customer incident communication | Scores/filings/service unavailable messaging |

## Mandatory CI checks (PR / main)

Required (not informational):

| Check | Workflow / job |
|-------|----------------|
| lint | `CI` / lint |
| unit-tests | `CI` / unit-tests |
| integration-tests | `CI` / integration-tests |
| single-alembic-head | `CI` + `alembic-single-head.yml` (when merged) |
| migration-contract | unit migration/rehearsal contract tests inside CI |
| rls-tenant-isolation | integration + `tenant-isolation.yml` (when merged) |
| legal-engine-p0 (single required branch-protection check; aggregates all four P0 jobs) | `legal-engine-assurance.yml` |
| legal-rule-catalogue-parity | `legal-engine-assurance.yml` |
| rjsc-scope-isolation | `legal-engine-assurance.yml` |
| score-provenance-integrity | `legal-engine-assurance.yml` |
| fail-closed-publication | `legal-engine-assurance.yml` |
| secret-scan | `secret-scan.yml` (when merged) |
| sast | `codeql.yml` (when merged) |
| dependency-audit | `security-dependency-audit.yml` |
| backend-frontend-contract | `api-contract.yml` + frontend CI |
| docker-runtime-smoke | `CI` (when present) |
| security-closure structure | `closure-structure.yml` |

**Not ordinary PR checks** (protected release stages):

- Isolated migration rehearsal 0112→head
- Live security closure (`check_security_closure.py` without `--structure-only`)
- Production environment approval
- Post-deploy tenant smoke + live rule parity

## Implementation order

| Priority | Work |
|----------|------|
| 1 | Fix failing CI; green run on exact PR SHA |
| 2 | Complete isolated 0112→head (0128) Neon rehearsal |
| 3 | Resolve competing auto vs controlled production deploy paths |
| 4 | Enforce live security closure + single-head on release |
| 5 | Make RLS, tenant isolation, legal-rule integrity required |
| 6 | Cross-repo API contract + frontend E2E |
| 7 | Automate restore drills + post-deploy assurance |
| 8 | SAST, secrets, SBOM, Dependabot |
| 9 | Worker, queue, load, continuous uptime |
| 10 | Ops, privacy, legal-content governance |

## Related docs

- `docs/LEGAL_ENGINE_ASSURANCE.md` — legal-engine P0 detail
- `docs/CI_PRODUCT_GAPS.md` — infrastructure gap map (when present)
- `docs/MIGRATION_RELEASE_CONTRACT.md` — migration release contract (when present)
