# NLC Production Readiness — Consolidated Open Issues

**Inspection date:** 2026-11-03  
**Scope:** Read-only Render and Neon inspection; GitHub code changes are proposed on a non-production branch.  
**Production changes:** None. No Neon migration, Render configuration change, deployment, or production data write was performed.

## Status summary

NLC is **not accepted as production-ready**. The production database's Alembic revision marker does not match sampled physical schema objects. The AGM held API/service mismatch and several legal-evidence defects have been patched on the review branch, but remain unmerged and undeployed pending full CI and review.

## Open issues

| ID | Priority | Workstream | Evidence | Status / acceptance condition |
|---|---|---|---|---|
| API-001 | P0 | AGM held endpoint | Current `main` route calls `AGMService.mark_held` with unsupported keyword names and fields; service expects `agm_date` and a different contract. | Patched in draft PR `fix/agm-schema-forward-reconcile-20261103`. Require passing CI and review before merge. |
| LEG-001 | P0 | AGM quorum | Companies Act 1994 s.85(2)(b) private-company statutory default differs by total membership: 2 members up to six; 3 members above six, subject to Articles. | Patched: engine and held-AGM service now return NOT_EVALUATED/NULL until current Articles are verified with reviewer identity, verification date and evidence reference; then use an Articles-specific quorum or the statutory default. Added evidence fields, migration columns and scenario tests. A controlled reviewer workflow/UI and counsel approval remain required before activation. |
| LEG-002 | P0 | AGM notice | Section 85 exceptions include accidental omission/non-receipt and shorter notice with required consent. | Patched defensively: short notice and missing dispatch records produce NOT_EVALUATED with zero score impact until member-level consent/exception evidence is captured. Full counsel-approved exception workflow and positive/negative scenarios remain open. |
| LEG-003 | P0 | First auditor | Section 210(6) uses one calendar month, not a fixed 30 days. | Patched: evaluator checks the actual appointment date against the calendar-month deadline; a Boolean without date evidence is NOT_EVALUATED, and conflicting status/date evidence is UNKNOWN. Audit API now accepts and returns the appointment date; CompanyProfile imports evidence from Audit records. Legacy seed/database descriptions are reconciled by 0045; counsel approval and deployed-version verification remain open. |
| LEG-004 | P0 | Legal provenance | Rules marked `RECONCILE` are not lawyer-approved merely because they are executable. | Require approved source, section, text/version, effective date, jurisdiction, reviewer identity/date and approval status for every active rule. |
| DB-001 | P0 | Production schema drift | Neon production branch `br-purple-fog-aodj8s04` reports Alembic `0042_dedup_key`, 32 base tables and 701 columns. Sampled physical catalog lacks 11 columns from migration 0031 and `notifications.deduplication_key` plus its unique index. | Confirmed mismatch. New migration 0045 proposes forward reconciliation of missing 0031–0033 company columns, 0035 verification fields, 0038 rescue audit table, 0041 rejected_by, 0036 tri-state evidence nullability and AGM held fields. Do not apply until tested on an isolated branch. |
| DB-002 | P0 | Neon branch differences | Vercel dev reports `0044_webhook_schema_reconcile`, 35 tables/753 columns and contains all sampled objects. Security-audit reports `0042_dedup_key`, 34 tables/727 columns; it has webhook tables and dedup DDL despite the older marker, but lacks legal verification fields, rescue_audit_log and rejected_by. Two sampled preview branches resemble production's 0042/32-table schema. | Investigate branch provenance, schema changes outside Alembic and exact app connection targets. Never assume branch names prove production use. |
| DB-003 | P0 | Migration validation capacity | Neon rejected a new branch request with HTTP 422 `branches limit exceeded`. | Blocked. Do not repurpose existing Vercel/security-audit branches without confirmation they are disposable. Obtain an approved disposable branch or increase branch capacity. |
| DEP-001 | P0 | Render release governance | NLC Render service is live on Free plan, one Docker instance in Singapore; auto-deploy disabled; deployed commit differs from GitHub main. | Keep manual deploy if intentional; document release approval, deployed SHA, rollback and post-deploy verification. |
| DEP-002 | P1 | Render health monitoring | Render service has no configured health-check path; application liveness endpoint was observed returning HTTP 200. | Configure after verifying liveness/readiness semantics and dependency behavior. |
| DEP-003 | P1 | Render observability/capacity | CPU/memory metrics were returned; queried HTTP request/latency series were empty. Service is single-instance Free plan. | Validate request metrics, alerting, tracing, backup/restore and capacity against a defined SLA. |
| SEC-001 | P0 | Tenant isolation | No complete cross-tenant authorization and PostgreSQL RLS penetration evidence has been established. | Patched on review branch: dashboard risk/deadline queries now apply active membership filters; company list, document and filing collection filters exclude revoked memberships. Added two-tenant integration tests for dashboard results and revocation across company/filing/document APIs. Full route-by-route/RLS/background-job penetration testing remains open. |
| AUD-001 | P0 | Audit history | No complete end-to-end proof of append-only integrity, actor attribution, tamper detection and event ordering has been established. | Require tamper tests, chain verification, identity binding, retention and restore evidence. |
| SEC-003 | P0 | Revoked membership handling | Several company access queries previously accepted a CompanyUserAccess row without checking is_active. | Patched on review branch in company list, document list/detail, filings list and legacy access dependency. Added regression coverage; verify all remaining access paths and deployed code. |
| AUD-002 | P0 | Evaluation-state integrity | ComplianceFlag defaulted eval_state to VIOLATION even when typed state was UNKNOWN. | Patched: typed UNKNOWN state now forces eval_state=UNKNOWN and zero score impact; regression assertion added. |
| OPS-002 | P1 | PDF rendering runtime | Render logs showed Fontconfig cache warnings about no writable cache directories. | Patched PDF renderer to use a writable ephemeral cache under /tmp before WeasyPrint import. Verify with a deployed PDF generation smoke test; not yet deployed. |
| CI-001 | P0 | Review-branch CI | Earlier runs exposed canonical adapter/test fixture defects; latest runs include migration and legal-evidence changes. | Current head must pass both unit and integration jobs, including clean PostgreSQL full Alembic upgrade. Do not merge based on an earlier commit's green status. |
| OPS-001 | P0 | Recovery | No successful production-equivalent restore drill has been established. | Restore a backup into an isolated environment; verify schema, records, evidence references, audit chain and measured RPO/RTO. |
| COM-001 | P1 | Commercial/legal controls | No complete customer contract, data processing terms, liability boundaries, security incident procedure or service-level commitments have been accepted. | Complete legal and operational review before enterprise claims or onboarding. |

| DB-006 | P0 | Non-idempotent rescue migration | Revision `b10c91ac6860` adds `companies.rescue_generation_error` without `IF NOT EXISTS`, but security-audit branch already contains the column while its Alembic marker remains 0042. | Read-only catalog check: security-audit has rescue column, dedup column/index and webhook tables while revision remains 0042; production has none of these objects and is also at 0042. | PATCHED IN DRAFT PR: migration now uses `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`. CI pending. Verify migration graph and all branch states before any Alembic upgrade. |

| DB-007 | P0 | ORM/schema defaults and unknown evidence | Historical 0031/0033 migrations and current Company ORM specify several boolean/member-count defaults (including `true` and `0`). The proposed 0045 adds missing factual columns as nullable/no-default, and re-applies 0036 tri-state nullability to nine sensitive booleans. | Source comparison confirms all 48 column names from 0031-0033 are covered, but physical nullability/defaults will not yet exactly match all current ORM declarations. | OPEN. Before calling schema reconciliation complete, reconcile ORM nullability/default semantics and evaluator treatment of NULL. Never backfill `true`, `false` or zero member counts as if they were verified evidence. |

| DB-008 | P0 | Historical migration reconciliation completeness | Production's 0042 marker masks missing 0035 verification fields, 0038 rescue audit table, 0041 rejected_by and 0036 nullability changes. 0034 calendar tables, 0039 evaluation_status, 0040 engagement_id and 0032/0033 sampled objects are present. | Targeted catalog comparison of production, Vercel dev and security-audit. | PATCHED IN DRAFT PR 104 migration 0045 for missing DDL and 0036 nullability; require migration execution test and schema diff before merge. The 0035 default PENDING is deliberately retained; never default to VERIFIED. |
| SEC-002 | P0 | Rescue audit tenant isolation | Historical 0038 creates `rescue_audit_log` with foreign keys and indexes but no RLS policy in that migration. | Direct inspection of migration 0038. | OPEN. Confirm API-level tenant authorization and add tenant-aware DB policy/role tests before using rescue audit log for cross-tenant customer data. |

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
