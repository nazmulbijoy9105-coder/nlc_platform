# NLC Current Status and Release Gap Register

**Reviewed:** 10 November 2026  
**Repository:** `nazmulbijoy9105-coder/nlc_platform`  
**Baseline:** `main` at `0e46a9ae19b134250a96e949551c321e32d3fc27`  
**Purpose:** Current engineering and documentation status. This register supersedes older status snapshots where they conflict; it does not approve legal rules or authorize production changes.

## 1. Release posture

**Product scoring: RELEASE ENABLED by product configuration. Legal verification: PENDING.**

The product release branch sets `LEGAL_SCORE_RELEASED = True` and enables the 82 score-bearing rules in `PRODUCT_SCORING_RULE_IDS`. AR-001 and SH-002 remain informational; ESC-003 is the internal surcharge/escalation rule and is not itself a scored finding.

`VERIFIED_RULE_IDS` remains empty. The legal approval register still has `approved_rule_ids: []`, with 85 records `REVIEW_REQUIRED` and `score_eligible: false`. Product scoring eligibility must not be represented as independent legal certification or counsel approval. The three non-scoring catalogue rules remain excluded by design.

This is an application scoring release, not a legal opinion or certification. Missing evidence remains UNKNOWN rather than proof of statutory non-compliance. AI-generated drafts remain subject to human review and approval. See [Product-controlled scoring release](release/PRODUCT_CONTROLLED_SCORING_RELEASE_2026-11-10.md) for the exact configuration and data/deployment scope.

This document is an engineering status record, not a legal opinion, counsel sign-off, production-readiness certificate, or permission to migrate/deploy.

## 2. Rule catalogue and production parity

Latest recorded read-only production-parity workflow: [GitHub Actions run 42690579660](https://github.com/nazmulbijoy9105-coder/nlc_platform/actions/runs/42690579660).

| Source | Active rule IDs |
|---|---:|
| Engine | 85 |
| Seed | 85 |
| Production API | 85 |
| Production database | 75 |

The recorded database comparison reported these 11 canonical IDs missing from the database:

`BOD-001`, `BOD-002`, `BOD-003`, `ACC-001`, `ACC-002`, `ACC-003`, `DIR-007`, `DIR-008`, `DIR-010`, `MEM-001`, `INC-007`.

It also reported legacy `INC-002` as an extra database ID. The recorded common intersection was 74 and union 86.

Migration `0049_reconcile_company_profile_and_rule_registry.py` appears intended to insert the 11 records as `PENDING` and deactivate the legacy record. The parity output alone does not prove whether migration 0049 has or has not been applied: inspect the actual Alembic revision and catalogue effects on the exact production database before deciding. Do not manually insert, delete, activate, or score rules to force parity. PENDING is not legal approval.

## 3. Documentation authority and superseded snapshots

Use this register together with the current source, migration graph, latest workflow evidence and legal approval register.

The following files are retained for audit history but must not be treated as current release authority:

| File | Required interpretation |
|---|---|
| `docs/LEGAL_AUDIT_SUMMARY.md` | Historical audit snapshot. Its “Engineering / rule-parity: GO” wording is not a production-release decision. |
| `docs/LAWYER_PENDING_REVIEW.md` | Historical issue list. Its statement that 82 rules were verified conflicts with the current 85/85 approval register, which has zero approved IDs. |
| `docs/PRODUCTION_READINESS_OPEN_ISSUES.md` | Historical issue snapshot based on 3 November / PR #103. Duplicate API-001 rows and old PR/CI/production observations require revalidation before reuse. |
| `docs/LAWYER_LEGAL_REVIEW_PACK.md` | Historical 75-rule pack; do not distribute as the current review pack. |
| `docs/RULE_CORPUS_GAP.md` | Historical 29-rule engine/seed gap from September; superseded by later 85-ID parity work. |
| `docs/RULE_IDENTITY_BUG_REPORT.md` | Historical rule-ID investigation; do not execute its old migration/repair recommendations without a fresh migration and data review. |
| `docs/release/NEON_PRODUCTION_REMEDIATION_RUNBOOK.md` | Historical production-specific runbook. Its expected head of 0073 is stale relative to the later migration inventory; re-derive the Alembic graph and actual production revision before any rehearsal. |

A historical observation must retain its original date, environment and evidence. Do not silently relabel it as a current finding or a closed issue.

## 4. Production migration and database integrity

The previous remediation runbook describes a production database observed at `0042_dedup_key` and an expected head of `0073`. The current repository inventory includes numbered migration files through `0088` and a timestamp-prefixed migration; filename ordering is not proof of Alembic ancestry or a single head.

Before any migration is considered:
1. Read the current `alembic_version` table from the exact production target using an authorized read-only connection.
2. Derive all Alembic heads, branch points, merge revisions and ancestry from the current repository.
3. Compare the full migration graph and expected schema with production catalog state; do not rely on a version marker alone.
4. Identify the actual Render runtime database target without exposing connection strings or credentials.
5. Restore a production recovery point into an isolated Neon branch and prove it can be queried.
6. Rehearse the complete candidate migration chain on that restored branch; capture row-count, constraint, index, trigger, RLS, view and application-role checks.
7. Investigate every unexplained difference. Do not stamp, skip, reorder, or manually rewrite revisions to force a green result.

No production migration, role/grant change, data repair or deployment is authorized by this register.

## 5. Rollback policy

The current rollback authority is `docs/ROLLBACK_RUNBOOK.md`.

- Application rollback and database rollback are separate operations.
- Redeploying an older application is allowed only after verifying that it is compatible with the current database schema and data.
- Do not use `alembic downgrade -1` as a generic production rollback. A downgrade can lose data, fail on forward-only migrations, or create an application/schema mismatch.
- Prefer a reviewed forward-fix migration for schema defects.
- For data corruption or destructive schema changes, use a verified Neon PITR restore into a separate branch, validate it, and plan a controlled cutover. Never overwrite the only production copy during investigation.
- A downgrade is an exceptional option only when the exact migration has a reviewed, tested, data-safe downgrade and the incident lead and authorized DBA explicitly approve it.

## 6. Legal-tech modelling requirements still requiring verification

These are modelling controls and open legal-source questions, not declarations that the current engine is legally correct:

| Topic | Required model / verification |
|---|---|
| AGM quorum | Apply the statutory default only after verified member count; retain operative Articles and meeting attendance evidence. Missing or conflicting facts remain UNKNOWN. |
| AGM notice | Model shorter-notice consent and accidental omission/non-receipt as distinct, evidence-backed exceptions; a notice boolean is insufficient. |
| First auditor | Use calendar-month semantics where the applicable provision requires a month; retain incorporation and appointment dates and verify the exact subsection against the operative Act text. |
| Director consent / RJSC forms | Keep statutory consent and Registrar filing as separate facts; preserve the Form IX / section-reference discrepancy pending primary-source reconciliation. |
| Board meeting frequency | A last-meeting date alone cannot establish the complete annual meeting count or spacing. Require a verified meeting history. |
| Directors' interests | Do not infer a universal register-of-interests duty from section 130 alone; identify the precise statutory duty and evidence required. |
| Share certificates | Cover both allotment and registered-transfer events and verify the applicable section, deadline and triggering date. |
| Capital increase | Calculate filing deadlines from the legally relevant resolution/decision date and verify the form/provision mapping. |
| Commencement declaration | Do not apply section 150 universally to private companies; model company type, prospectus/public-company status and applicability. |
| Strike-off | Annual-return arrears alone do not prove that Registrar strike-off proceedings have commenced; require authenticated notice/service or official register evidence. |
| Charge satisfaction | Distinguish charge creation/registration from satisfaction and identify the correct statutory filing trigger. |

For each rule, preserve applicability, exceptions, evidence provenance, effective date, uncertainty and legal disposition separately. Use explicit states such as `NOT_APPLICABLE`, `UNKNOWN`, `DISPUTED`, `REQUIRES_LAWYER_JUDGMENT` and `VERIFIED_ABSENT`. Never convert a missing upload into a verified absence.

## 7. Engineering closure register

| Priority | Workstream | Closure evidence |
|---|---|---|
| P0 | Production rule parity | Actual production revision + read-only catalogue comparison; explain all 11 missing IDs and legacy extra without manual data edits. |
| P0 | Alembic integrity | Exactly understood heads/ancestry; production-derived restore rehearsal; no unexplained schema/data drift. |
| P0 | Tenant isolation and RLS | PostgreSQL-backed negative tests for cross-tenant reads/writes; actual runtime role; forged-identity and worker-context tests. |
| P0 | Runtime and audit security | Exactly scoped RLS policies, actor/tenant provenance, append-only audit evidence, and role privilege verification. |
| P1 | Workflows and reports | End-to-end tests for onboarding, AGM, audit, returns, evidence, rescue, approvals and report/evaluation snapshot consistency. |
| P1 | Operations | Verified restore, worker lifecycle, health/readiness semantics, alert thresholds/destinations and delivery tests. |
| P1 | Frontend/backend parity | Evidence-review language, API response contracts, authorization, loading/error states and no misleading risk cards while release is closed. |
| P1 | Repository hygiene | Reference-aware unused-file audit across all related repositories; classify candidates before deletion. |

A workstream is not closed because a file exists or a test was once reported green. Closure must cite the exact current commit, command/workflow, environment, result and any relevant legal/operational evidence.

## 8. Explicit non-actions

This register does not:
- approve any legal rule or enable `LEGAL_SCORE_RELEASED`;
- change `approved_rule_ids`, `VERIFIED_RULE_IDS` or legal calendar release;
- authorize production SQL, migrations, grants, role changes, data repair or deployment;
- claim all legal sources/amendments are current;
- claim the platform is production-ready.

**Current posture: engineering remediation and evidence review continue; statutory scoring remains NOT RELEASED.**
