# NLC G2/G3 infrastructure and legal-review rebaseline — 27 November 2026

**Repository baseline:** `main` at `80c22bb46552295888b5f2e25ef77e83108519ff`  
**Purpose:** Separate isolated-PostgreSQL engineering assurance from live-service smoke checks and independent legal review. This is an evidence-based project status note, not a legal opinion, counsel sign-off, or production deployment authorization.

## Executive disposition

- **G2 — engineering verification:** Not blocked on Neon. Alembic head, PostgreSQL RLS, tenant isolation, catalogue parity, scope injection, evaluation/hash integrity and withheld-score tests can run against disposable PostgreSQL in GitHub Actions. The main CI workflow already provisions PostgreSQL 16; this change set moves the repeated migration rehearsal and role audit away from Neon as well. G2 is **ready for CI closure**, but is not marked closed until the exact branch workflow succeeds with zero skips.
- **Live smoke:** Health/readiness, CORS and reverse-proxy checks remain checks against the deployed Render service. Readiness currently cannot pass because the deployed service cannot connect to Neon while the Neon quota is exceeded.
- **G3 — independent legal review:** **OPEN / critical path.** The legal approval register has 85/85 rules marked `REVIEW_REQUIRED`, `score_eligible: false`, and `approved_rule_ids: []`. `VERIFIED_RULE_IDS` is empty. This is weeks of reviewer work, not a 1 December automatic gate.
- **Reviewer identity:** ChatGPT is not Bangladesh-qualified counsel and cannot act as, or sign for, reviewing counsel. No counsel approval is claimed here. If the rule author has reviewed a rule, that must be recorded separately as **AUTHOR_REVIEWED**, with author identity, date and scope; it is not independent counsel approval.

## Neon transfer and compute evidence

Neon project `rapid-bonus-26545234` (`NLC`, region `aws-ap-southeast-1`, plan `free_v3`) reports for the 1 November–1 December 2026 consumption period:

| Project metric | Reported value |
|---|---:|
| Data transfer | 5,551,438,402 bytes (about 5.17 GiB) |
| Compute time | 205,957 seconds (about 57.2 hours) |
| Active time | 794,184 seconds (about 220.6 hours) |
| Written data | 0 bytes |

The visible branch records report 420,915,203 bytes for the production branch; 69,747 bytes for the pre-0122 backup branch; 499 bytes for the 0126/0127 rehearsal branch; and 542,485 bytes for the archived legal-remediation rehearsal branch. The project-level transfer total is therefore about 5.13 GB above the sum of those visible branch counters. These counters do not provide a reliable attribution to individual workflows or prove that every historical/deleted branch is represented.

Neon's per-project consumption breakdown endpoint returned HTTP 403 because detailed consumption is not available on the current free plan. Therefore the exact byte contribution by workflow cannot be established from the available billing telemetry. Do not present an exact workflow-to-byte attribution as fact.

### Most likely avoidable CI source

The workflow `.github/workflows/production-0112-to-0122-rehearsal.yml` created disposable Neon child branches from the production-derived backup branch and rehearsed Alembic on each run. In the first 1,000 recent GitHub Actions runs returned for the repository with `created >= 2026-11-20`, I counted **at least 168 executions** of this workflow path (the workflow display name changed as the target migration revision changed). Each run performed Neon API branch/endpoint operations and database work. This is the strongest identified recurring CI source of additional Neon compute and branch-related transfer.

A second direct production-database consumer was `.github/workflows/neon-role-membership-audit.yml`, scheduled every six hours (up to four production DB audit connections per day). The daily encrypted backup workflow also runs `pg_dump` against the deployed Neon database; that is a backup operation, not a test suite, and remains a separately identified read-only operational exception. The manual backup workflow is also retained as an operator action.

## Render restart evidence

For Render service `srv-d72sam94tr6s73dk8etg` (`nlc_platform`), the 100 newest service events in the inspected window contained 91 `server_failed` events and 9 `server_available` events between 27 November 2026 03:49 and 06:50 UTC. Failures carried `nonZeroExit: 3` across multiple instance IDs.

The application log at 06:50:47 UTC records startup failure in `app/main.py`'s lifespan handler:

`RuntimeError: Cannot connect to database on startup ... Your account or project has exceeded the quota. Upgrade your plan to increase limits.`

This confirms a restart loop caused by the database quota response, not an inferred memory or health-check failure. The app exits before becoming ready. No Render service configuration, Neon plan, production environment variable or deployment was changed in this investigation.

## G2 closure matrix — isolated PostgreSQL only

| Check | Required CI evidence | Neon required? |
|---|---|---:|
| Alembic graph/head | Exactly one repository head; fresh PostgreSQL upgrade to head; second upgrade idempotent; current revision equals head | No |
| RLS and role posture | PostgreSQL role attributes, role-membership audit, policies and table security tests | No |
| Tenant isolation | Negative cross-tenant read/write tests, forged identity and worker-context tests | No |
| 85/85 rule parity | Engine/seed/database/API canonical-ID parity tests on a seeded test database | No |
| Scope injection | Inject OUT_OF_SCOPE rules and prove score, risk band, rescue and hash remain unchanged | No |
| Hash tamper detection | Mutate canonical evaluation inputs/hash and prove integrity validation rejects it | No |
| Withheld-score behaviour | NOT_EVALUATED/UNKNOWN/insufficient-evidence states produce no released statutory finding or score; no skipped tests | No |

The existing main CI workflow already provisions a PostgreSQL 16 service and runs fresh-database Alembic upgrades plus PostgreSQL security/integration tests. The revised G2 workflow makes the migration/legal-engine subset independently runnable without Neon. The role-membership audit is also moved to local PostgreSQL and removed from the six-hour production schedule.

**G2 closure rule:** mark each row closed only after the new PostgreSQL workflow and the main CI run pass on the same candidate SHA, the required tests are collected, and the G2 suite reports zero skips. Do not wait for Neon to close these rows.

**Live smoke remains separate:** Render health/readiness, CORS and proxy checks must be run against the deployed service after Neon connectivity is restored. A local PostgreSQL pass cannot establish deployed ingress or live database readiness.

## G3 — accountable owner and dated review plan

**Current status:** 0/85 independent counsel approvals; 85/85 require review. The existing `docs/legal/85_RULE_COUNSEL_VALIDATION_DOCKET.md` is a research docket, not signed approval.

| Milestone | Accountable owner | Target date | Exit evidence |
|---|---|---:|---|
| Appoint independent Bangladesh-qualified company-law reviewer and agree engagement/scope | Project owner | 1 December 2026 | Named reviewer, credentials/chamber, conflict check, accepted scope and written timetable |
| Prioritise material rules and freeze the review pack/version | Project owner + independent reviewer | 3 December 2026 | Versioned 85-rule dossier, primary-source bundle, amendment chronology and priority order |
| Complete first material-rule review batch | Independent reviewer | 11 December 2026 | Rule-specific signed dispositions, scope, exceptions, evidence, remedy and test-vector approval |
| Complete remaining rule-by-rule review and reconcile author comments | Independent reviewer; project owner tracks remediation | 31 December 2026 (provisional planning target) | 85 individual dispositions; rejected/limited rules remain non-scoreable; signed approval register and source hashes |

The dates after appointment are **planning targets, not a representation that counsel has accepted the engagement or guaranteed completion**. Rebaseline them with the appointed reviewer. G3 does not clear merely because the calendar reaches 1 December.

The author and independent reviewer must be different people for the independent-counsel status. The author's own work may be documented as `AUTHOR_REVIEWED`; it must never be relabelled `COUNSEL_APPROVED`. Every rule needs its own disposition; a module-level or blanket signature does not approve all 85 rules.

## Important scoring-control distinction

The current engine source sets `LEGAL_SCORE_RELEASED` default to `true` (`app/rule_engine/engine.py`), and `scripts/check_rule_verification.py` explicitly enforces that product-scoring configuration. Separately, `VERIFIED_RULE_IDS` remains empty and the legal approval register keeps all 85 rules non-score-eligible.

Accordingly, product-owner-enabled risk scoring is not proof of independent legal validation. UI, API and reports must continue to identify it as an NLC product-risk score, not a counsel-approved legal opinion or statutory compliance certificate. G2's withheld-score tests must still prove that unknown, not-evaluated, disputed and insufficient-evidence states do not become adverse statutory findings.

## Changes in this branch

- Replaced the PR-triggered Neon production-derived migration rehearsal with a PostgreSQL 16 service-container G2 workflow.
- Added the read-only role-membership SQL audit to the existing PostgreSQL-backed main CI job.
- Replaced the six-hour Neon production role audit with a manual, isolated-PostgreSQL audit workflow.
- Retired the manual Neon-backed Alembic and restored-snapshot rehearsal workflows from routine GitHub Actions. The daily encrypted backup remains a separately scoped operational backup, not a CI test.
- No Neon database, Render service, production environment variable, migration or deployed instance was changed.

## Explicit non-claims

- No exact per-workflow byte attribution is available from the current Neon free-plan telemetry.
- G2 is not closed until the branch CI runs pass.
- G3 is not counsel-approved; no reviewer has signed the 85-rule docket.
- No production deployment, database migration or quota upgrade was performed.
