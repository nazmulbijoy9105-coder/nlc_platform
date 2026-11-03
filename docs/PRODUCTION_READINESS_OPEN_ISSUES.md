# NLC Production Readiness — Consolidated Open Issues

**Inspection date:** 2026-11-03  
**Scope:** Read-only Render and Neon inspection; GitHub code changes are proposed on a non-production branch.  
**Production changes:** None. No Neon migration, Render configuration change, deployment, or production data write was performed.

## Status summary

NLC is **not accepted as production-ready**. The production database's Alembic revision marker does not match sampled physical schema objects, and the current `main` AGM held endpoint has a confirmed API/service contract mismatch.

## Open issues

| ID | Priority | Workstream | Evidence | Status / acceptance condition |
|---|---|---|---|---|
| API-001 | P0 | AGM held endpoint | Current `main` route calls `AGMService.mark_held` with unsupported keyword names and fields; service expects `agm_date` and a different contract. | Patched in draft PR `fix/agm-schema-forward-reconcile-20261103`. Require passing CI and review before merge. |
| LEG-001 | P0 | AGM quorum | Companies Act 1994 s.85(2)(b) private-company statutory default differs by total membership: 2 members up to six; 3 members above six, subject to Articles. | Proposed code derives default from positive recorded member_count and labels result provisional until Articles are reviewed. Need legal counsel validation of interpretation and Articles-specific override workflow. |
| LEG-002 | P0 | AGM notice | Section 85 exceptions include accidental omission/non-receipt and shorter notice with required consent. | Existing rule descriptions/evaluator still require full legal reconciliation and scenario tests. |
| LEG-003 | P0 | First auditor | Section 210(6) uses one calendar month, not a fixed 30 days. | Earlier engine change identified; verify every active seed, canonical rule, evaluator and deployed rule version agrees. |
| LEG-004 | P0 | Legal provenance | Rules marked `RECONCILE` are not lawyer-approved merely because they are executable. | Require approved source, section, text/version, effective date, jurisdiction, reviewer identity/date and approval status for every active rule. |
| DB-001 | P0 | Production schema drift | Neon production branch `br-purple-fog-aodj8s04` reports Alembic `0042_dedup_key`, 32 base tables and 701 columns. Sampled physical catalog lacks 11 columns from migration 0031 and `notifications.deduplication_key` plus its unique index. | Confirmed mismatch. New migration 0045 proposes additive reconciliation of missing 0031–0033 company columns and AGM held fields. Do not apply until tested on an isolated branch. |
| DB-002 | P0 | Neon branch differences | Vercel dev reports `0044_webhook_schema_reconcile`, 35 tables/753 columns; security-audit reports `0042_dedup_key`, 34 tables/727 columns, but has webhook tables with RLS enabled. Two sampled preview branches resemble production's 0042/32-table schema. | Investigate branch provenance, schema changes outside Alembic and exact app connection targets. Never assume branch names prove production use. |
| DB-003 | P0 | Migration validation capacity | Neon rejected a new branch request with HTTP 422 `branches limit exceeded`. | Blocked. Do not repurpose existing Vercel/security-audit branches without confirmation they are disposable. Obtain an approved disposable branch or increase branch capacity. |
| DEP-001 | P0 | Render release governance | NLC Render service is live on Free plan, one Docker instance in Singapore; auto-deploy disabled; deployed commit differs from GitHub main. | Keep manual deploy if intentional; document release approval, deployed SHA, rollback and post-deploy verification. |
| DEP-002 | P1 | Render health monitoring | Render service has no configured health-check path; application liveness endpoint was observed returning HTTP 200. | Configure after verifying liveness/readiness semantics and dependency behavior. |
| DEP-003 | P1 | Render observability/capacity | CPU/memory metrics were returned; queried HTTP request/latency series were empty. Service is single-instance Free plan. | Validate request metrics, alerting, tracing, backup/restore and capacity against a defined SLA. |
| SEC-001 | P0 | Tenant isolation | No complete cross-tenant authorization and PostgreSQL RLS penetration evidence has been established. | Require two-tenant positive/negative tests for every company-scoped API, report, export, file and background task; test database role/RLS bypass paths. |
| AUD-001 | P0 | Audit history | No complete end-to-end proof of append-only integrity, actor attribution, tamper detection and event ordering has been established. | Require tamper tests, chain verification, identity binding, retention and restore evidence. |
| OPS-001 | P0 | Recovery | No successful production-equivalent restore drill has been established. | Restore a backup into an isolated environment; verify schema, records, evidence references, audit chain and measured RPO/RTO. |
| COM-001 | P1 | Commercial/legal controls | No complete customer contract, data processing terms, liability boundaries, security incident procedure or service-level commitments have been accepted. | Complete legal and operational review before enterprise claims or onboarding. |

| DB-006 | P0 | Non-idempotent rescue migration | Revision `b10c91ac6860` adds `companies.rescue_generation_error` without `IF NOT EXISTS`, but security-audit branch already contains the column while its Alembic marker remains 0042. | Read-only catalog check: security-audit has rescue column, dedup column/index and webhook tables while revision remains 0042; production has none of these objects and is also at 0042. | PATCHED IN DRAFT PR: migration now uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. CI pending. Verify migration graph and all branch states before any Alembic upgrade. |

## Database reconciliation detail

### Sampled missing columns on production

- Migration 0031: `last_board_meeting_date`, `board_meeting_notice_given`, `board_minutes_prepared`, `financial_statements_presented`, `financial_statements_filed`, `books_of_account_kept`, `director_consent_filed`, `director_office_of_profit`, `managing_director_appointment_date`, `member_count`, `business_commencement_declaration_filed`.
- Migration 0042: `notifications.deduplication_key` and `ix_notifications_dedup_key` were absent on production at inspection.
- Proposed AGM fields: `agms.venue`, `agms.accounts_adopted`, `agms.agm_held_without_audit`, `agms.quorum_basis`.

Migration 0043 is designed to reconcile the notification key/index, and 0044 creates/reconciles webhook tables and RLS. Production was at 0042 at inspection. The new 0045 is deliberately forward-only and adds missing historical company fields as nullable values so it does not invent compliance evidence. It must still be exercised through the actual Alembic runner on a disposable branch.

### Important limitations

- Catalog comparisons were read-only and limited to named columns/tables; this is not a complete schema equivalence proof.
- The application database connection target for Render and Vercel has not been verified by reading secret values (and secret values must not be exposed).
- Existing Neon branch capacity prevented creation of a fresh migration-validation branch.
- Passing CI for a previous PR or commit does not establish that this new branch passes CI.
- No migration has been run on production.

## Release gate

A production release is blocked until all P0 issues have evidence-backed acceptance, the migration is tested against a disposable database branch, legal rules are counsel-approved, tenant isolation is demonstrated, and a rollback/restore drill passes.
