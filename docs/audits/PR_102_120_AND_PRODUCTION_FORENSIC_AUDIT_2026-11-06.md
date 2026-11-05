# NLC PR #102–#120 and production forensic audit

**Audit date:** 6 November 2026  
**Repository:** `nazmulbijoy9105-coder/nlc_platform`  
**Mainline baseline for remediation PR #125:** `51c7e6cb20a5d50b6366afae480b927e35d0d11f`  
**Remediation PR:** [#125](https://github.com/nazmulbijoy9105-coder/nlc_platform/pull/125) — draft; do not merge or deploy until every release condition below passes.

## 1. Executive disposition

The repository and live database are **not release-ready**. This audit confirmed a live tenant-identity forgery bypass, a production migration gap, a stale/incomplete rule catalogue, excessive runtime grants, and multiple legal-rule mapping/evidence defects.

No production database role, grant, policy, rule row, migration state or Render service was changed during this audit. All repository remediation described here is on PR #125.

## 2. PR #102–#120 disposition

A PR marked merged is not automatically proof that every original functional change remains in current `main`. A merge into a feature branch is not a merge into `main`; an empty PR diff is not an implementation.

| PR | GitHub disposition | Forensic interpretation |
|---|---|---|
| #102 | Closed, not merged | 158-commit branch; no release credit without file-level ancestry/diff proof. |
| #103 | Merged | AGM quorum and first-auditor corrections reached mainline; current statutory/evidence implementation still requires review. |
| #104 | Closed, not merged | Superseded; do not treat as mainline implementation. |
| #105 | Closed, not merged | 428-commit AGM/Articles/evidence/RLS branch; review comments identify the ADMIN-sentinel UUID-cast issue and unsafe activity-log policies. Its full-document S3 upload approach also conflicts with the no-upload policy in #109; do not cherry-pick it. |
| #106 | Closed, not merged | Dashboard isolation work not merged through this PR. |
| #107 | Closed, not merged | Signed-RLS feature branch; not a mainline release source. |
| #108 | Not retrievable | GitHub returned 404; no incorporation claim can be made. |
| #109 | Closed, not merged | Workflow specification only. It explicitly prohibits uploading complete MOA/AOA and original RJSC-issued records; implement NLC-only hard-copy examination records instead. |
| #110 | Merged | Its own changed-file list is empty; no functional change can be attributed to this PR alone. |
| #111 | Closed, not merged | Proposed charge-satisfaction mapping to Companies Act section 87(2) is wrong; section 87 concerns extraordinary resolutions, while section 172 is the charge-satisfaction anchor. |
| #112 | Closed, not merged | Dashboard isolation branch; its own description said CI had not run. |
| #113 | Merged | Dashboard tenant scoping and AGM unknown-default changes reached mainline; production RLS still independently failed the direct SQL test below. |
| #114 | Closed, not merged | 170-commit legal remediation branch; later consolidation does not prove all legal corrections survived. |
| #115 | Closed, not merged | Legal scoring/parity branch; not a release source. |
| #116 | Closed, not merged | BLACK override/PDF reconciliation work requires file-level confirmation in the current code. |
| #117 | Merged | Large P0 consolidation; included overlapping migration branches and must be assessed with the final Alembic graph, not filename counting. |
| #118 | Merged | Mainline release-gate consolidation; subsequent mainline divergence/regression is visible in the engine and service files. |
| #119 | Closed, not merged | Migration/Docker patch is not mainline. Its Docker patch has duplicate `XDG_CACHE_HOME` assignments and should not be cherry-picked blindly. |
| #120 | Merged into #107's signed-RLS branch | **Not merged into main.** Its ActivityService exception-propagation behavior is nevertheless present in the current mainline file; verified by direct file comparison. |

### Missing-work and history cautions

- Large unmerged branches (#102, #105, #107, #114) are not sources of truth.
- #120's feature-branch merge cannot be counted as a mainline merge; its ActivityService exception-propagation behavior was separately confirmed present in main.
- #110 has no changed files in its own PR diff.
- #117/#118 introduced multiple migration branches. PR #119 proposed another merge revision over already-merged parents and a malformed Dockerfile environment block; it was not restored. PR #125 CI must prove one head and two clean upgrades.
- The current mainline engine differs from the earlier #118 branch version in material evaluator sections. PR #125 restores evidence-gated AGM, charge, tax, labour and BSEC behavior selectively; this is not proof that every historical change has been reconciled.
- Use `git range-diff`, `git diff --find-renames`, full migration ancestry and current-file comparison. `git log origin/main..branch` alone is insufficient to prove functional inclusion.

## 3. Confirmed live Neon production findings (read-only)

### 3.1 Migration and schema drift

- Neon branch named production reports alembic_version = 0042_dedup_key; current mainline migration head is 0057_merge_final_heads, and PR #125 adds migration 0058 for notification suppression.
- The live legal_rules schema is behind the current ORM model; verification-status/evidence columns expected by the model are absent.
- Render service nlc_platform is on branch main with automatic deploy disabled. Latest successful deploy observed: commit 9e4f99d; later deploy attempts for 51c7e6c failed.
- Render logs contain three blockers: at 19:37 UTC, NLC_RLS_HMAC_SECRET was missing/shorter than 32 characters; at 19:43 UTC, permission denied to alter role; and from 19:48 UTC, Can't locate revision identified by 0049_evaluation_runs_and_identity_rls. The referenced migration file exists in the GitHub tree at 51c7e6c, and PR #125 CI has since passed single-head/fresh-upgrade checks. The Render artifact/database target mismatch is unresolved; confirm the exact Render image and database URL before deployment. Do not assume the Neon branch inspected here is necessarily the database used by Render.
- Production must be backed up and upgraded through the exact tested chain. Do not stamp revisions, skip migrations or apply role DDL from Alembic.

### 3.2 Tenant identity forgery — P0 confirmed

The test was executed directly as `nlc_app_role`:

| Query context | Visible companies | Visible compliance flags | Visible score-history rows |
|---|---:|---:|---:|
| No identity GUC | 0 | 0 | — |
| `app.current_user_id='ADMIN'` only, no signature | 23 | 434 | 51 |

The current production policies trust the caller-settable identity GUC. An ordinary SQL session can forge the `ADMIN` sentinel and read tenant data. This is a reproducible vulnerability, not a theoretical concern.

Migration 0050 replaces raw-GUC trust with an HMAC-verified principal, recreates tenant policies, enables and forces RLS, and revokes dangerous table privileges. After migration, repeat the exact exploit test and prove that an unsigned `ADMIN` GUC returns zero rows.

### 3.3 RLS and privilege posture

- The read-only inspection session was neondb_owner (BYPASSRLS=true). This proves the inspection credential is privileged; it does not by itself prove Render's runtime session. pg_stat_activity showed no separate Render application session at inspection time, so the actual Render connection identity remains unverified.
- nlc_app_role and nlc_ci_audit_role both exist and are LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION and NOBYPASSRLS, but both currently have INHERIT=true. Migration 0050's read-only preflight requires NOINHERIT; an authorised Neon administrator must change both roles out-of-band before migration. Do not weaken the preflight.
- neondb_owner is a member of nlc_app_role and nlc_ci_audit_role with admin option; neither application role is a member of neondb_owner.
- nlc_app_role has grants across 37 tables, including DELETE, REFERENCES, TRIGGER and TRUNCATE. Migration 0050 explicitly revokes TRUNCATE, REFERENCES and TRIGGER and removes selected DELETE privileges; verify effective grants after upgrade. RLS does not protect TRUNCATE.
- 30 of 32 public tables currently have RLS enabled; zero have FORCE RLS.
- Eight RLS-enabled tables have no policy, including company_user_access, legal_rules, legal_rule_versions, users, quotations, compliance_events and activity/audit tables.
- compliance_calendar_events has a company_id column but RLS is disabled in production. Migration 0050 includes it in the tenant table set; verify post-upgrade policy and FORCE RLS.

### 3.4 Legal-rule catalogue drift

- Repository seed defines 85 rule IDs; production has 75 active.
- Missing active IDs: `BOD-001`, `BOD-002`, `BOD-003`, `ACC-001`, `ACC-002`, `ACC-003`, `DIR-007`, `DIR-008`, `DIR-010`, `MEM-001`, `INC-007`.
- Extra active ID: `INC-002`; its origin and use must be established before an audited retirement.
- All 75 active production rows have non-zero score impacts; 13 are BLACK.
- `legal_rule_versions` has zero rows; `last_modified_by` and `last_modified_at` are unset on current rule rows.
- The legal approval register has zero approved rule IDs. The production database must not present the existing rule scores as counsel-approved.

The seeder previously updated existing legal-rule rows without writing immutable version snapshots. PR #125 changes it to insert-only and fail on drift; existing changes must go through the authenticated Super Admin workflow with actor, reason, previous definition and version increment.

### 3.6 Queued customer notifications

- Production contains 476 queued notifications whose `notification_type` is a legal rule ID: 139 EMAIL and 337 DASHBOARD. None has `sent_at` set; the queue is pending, not delivered.
- PR #125 filters unapproved rule alerts from user/admin notification APIs, prevents worker delivery, adds a `SUPPRESSED` status and migration 0058 suppresses existing pending rule notifications. Non-legal operational notifications are not suppressed by the rule-ID pattern.
- Production queue rows have not been modified by this audit. Migration 0058 must be applied before any notification worker is restarted.

### 3.5 Stored scores and history

- All 23 companies currently have numeric cached scores (range 0–50); none has a NULL score.
- All 51 history snapshots are numeric, the latest is 1 October 2026, and none has `evaluation_status='NOT_EVALUATED'`.
- 14 of 23 companies have a current cached score different from their latest history score.
- Current flags: 129 BLACK, 194 RED and 111 YELLOW.
- Migration 0052 clears cached company scores and sets risk band to `NOT_EVALUATED`. Migration 0051 makes history scores nullable but intentionally preserves immutable pre-release history. API serializers must continue returning NULL/NOT_EVALUATED until legal release.
- PR #125 adds explicit PDF and automated-rescue release guards because relying on the database invalidation migration alone would leave a window in which old stored scores could be used.

## 4. Legal source corrections and fail-closed treatment

This pass checked primary-source anchors for the following high-risk rules. It is source triage, not independent counsel approval:

| Area | Correct legal anchor / finding | Required engine treatment |
|---|---|---|
| AGM quorum | Companies Act 1994, s.85(2)(b); defaults apply only where Articles do not provide otherwise. Section 89 is not the quorum provision. | Verify operative Articles, member count and authenticated attendance. |
| AGM adjournment | Section 85 and the company Articles are candidate sources; exact adjournment-notice duty and consequence require counsel review. | `NOT_EVALUATED`; no automatic breach. |
| First auditor | Companies Act 1994, s.210(6); first auditor appointed by Board within one month of registration, subject to the statutory details. | Keep distinct from subsequent AGM auditor appointments and Registrar notice duties. |
| Board meetings | Companies Act 1994, s.96: at least one meeting every three months and at least four per year. | Complete verified meeting history is required; a single last-meeting date cannot prove compliance. |
| Board notice/minutes | Sections 95 and 89 respectively. | Verify notice service to directors then in Bangladesh and minute-book evidence; missing upload is not proof of non-creation. |
| Director interests | Section 130 concerns disclosure of interest in company contracts/arrangements; it does not by itself establish a generic register-of-directors-interests duty. | Rename/reshape or retain as review-only until exact duty and evidence are established. |
| Contracts register | No universal generic register duty established in this pass. Sections 97/98 are not generic register anchors. | `NOT_EVALUATED`; no automatic default. |
| Office of profit | Section 104 includes role-specific exclusions and general-meeting consent requirements. | Verify exact office, statutory exclusion and consent. |
| Managing director term | Section 110: five years at a time. | Verify current appointment instrument, reappointment and continuity. |
| Charge satisfaction | Section 172(1): notice to Registrar within 21 days of payment/satisfaction of a registrable charge; distinguish section 159 creation/registration and foreign-company provisions. | Missing satisfaction date = UNKNOWN; no breach before deadline. |
| BSEC | Code 2018: Condition 1 board composition; Condition 5 Audit Committee; Condition 8 company website; Condition 9 annual certificate/reporting. Listed-issuer scope. | Do not map quarterly filing to Condition 8; identify separate listing instrument. |
| Income tax return | Income Tax Act 2023, s.170(2)/171 as substituted by Finance Act 2026 (Act 96/2026): non-individual deadline is 15th day of ninth month after income-year end, but not earlier than following 15 September. | Review prompt; verify taxpayer class, income-year, holidays and extensions. |
| VAT thresholds | VAT Act 2012 as amended by Act 77/2026: BDT 30 lakh turnover-tax enlistment and BDT 50 lakh registration thresholds, subject to taxpayer class and mandatory categories. | Verify rolling 12-month taxable turnover and mandatory categories; annual turnover alone is insufficient. |
| VAT return cadence | VAT Amendment Ordinance 38/2026 (14 October 2026) substituted section 64: each tax period; 15-day rule and specified 20-day classes, holiday roll-forward and Board extension. | Do not use the superseded three-tax-period formulation. |
| Factory licensing | Bangladesh Labour Act 2006, s.326 as amended by Act 43/2026; licensing is direction-based for specified institution/factory/class. | Require the applicable Government direction and establishment-class evidence; not universal. |
| Strike-off | Companies Act 1994, s.346 governs the Registrar's defunct-company removal process, including statutory inquiry/follow-up and Gazette/show-cause steps. Section 304 concerns liquidator reporting duties, not strike-off. | Backlog alone is not proof of proceedings. Require authenticated Registrar correspondence, service, Gazette notice, expiry of the 90-day show-cause period and current register status; no automatic BLACK. |

Official source entry points:
- [Companies Act 1994 — BDLaws](https://bdlaws.minlaw.gov.bd/act-print-788.html)
- [Companies Act section 85 — BDLaws](https://bdlaws.minlaw.gov.bd/act-print-788/section-print-32909.html)
- [Companies Act section 346 — BDLaws](https://bdlaws.minlaw.gov.bd/act-print-788/section-print-33170.html)
- [BSEC Corporate Governance Code 2018 — official PDF](https://www.sec.gov.bd/slaws/Corporate_Governance_Code_10.06.2018.pdf)
- [Income Tax Act 2023 — BDLaws](https://bdlaws.minlaw.gov.bd/act-print-1725.html)
- [VAT Amendment Act 2026 — BDLaws](https://bdlaws.minlaw.gov.bd/act-print-1706.html)
- [VAT Amendment Ordinance 2026, section 64 — BDLaws](https://bdlaws.minlaw.gov.bd/act-1742/section-59742.html)
- [Bangladesh Labour (Amendment) Act 2026 — BDLaws](https://bdlaws.minlaw.gov.bd/act-print-1672.html)

## 5. Additional omitted-work findings

- PR #105's Articles/AGM evidence implementation is absent from mainline. Its PDF upload route is not suitable for restoration because it conflicts with the no-upload policy. The replacement design must record physical document identity/type, presenter, custody/return, pages/clauses examined, examiner, independent reviewer, effective date, provenance, limitations and unresolved facts without storing full document bytes.
- Current AGM API serializers hide quorum/member counts unless attendance and quorum basis have separate verification markers. The service still computes a provisional statutory-default estimate from the company's stored member count; that value is not exposed as a verified result. Any future Articles workflow must not convert this estimate into a legal conclusion without hard-copy review.
- Current signed-RLS code sets SET LOCAL ROLE nlc_app_role, signs UUID/service principals with NLC_RLS_HMAC_SECRET, rechecks active membership and compares the live database role to the token role. The startup role check must be proven against the actual Render connection; NLC_RLS_HMAC_SECRET must be at least 32 characters and remain stable across app instances.

## 6. Changes currently on PR #125

- Removed role creation/alteration/membership grant from migration 0050; added read-only preflight.
- Fixed the PostgreSQL CI `DO $$ ... $$;` syntax.
- Restored evidence-gated AGM, charge, tax, labour and BSEC evaluators from the prior legal remediation.
- Added a global closed release gate to score-impact reporting and kept `VERIFIED_RULE_IDS` empty pending counsel approval.
- Suppressed provisional customer RED/BLACK alerts until legal score release and rule eligibility.
- Implemented the missing system deadline query.
- Quarantined AGM adjournment, Board evidence, director-register, office-of-profit, MD-term and strike-off findings as `NOT_EVALUATED` where the profile lacks sufficient evidence or legal mapping.
- Updated seed and canonical rule metadata; the seed script now refuses unversioned updates.
- Updated legal basis matrix, 85-rule source triage, evidence mappings and production release runbook.

## 7. CI and production release gates

At the time of this audit:
- A previous PR #125 run passed compile, single Alembic head, two fresh PostgreSQL upgrades, integration/RLS tests, canonical integrity tests and Docker runtime smoke.
- Its unit job exposed two failures (DIR-005 engine/seed text parity and the scoring-gate test patch target); both were corrected in subsequent commits.
- The latest exact-head CI run must complete successfully. No passing status is claimed until that run is complete.

Before merge/deploy, require:
1. All CI jobs green on the exact PR head, including static engine/seed parity and the empty rule-verification check.
2. A tested upgrade from a production-equivalent snapshot at revision 0042 through the current single Alembic head.
3. Out-of-band change of both `nlc_app_role` and `nlc_ci_audit_role` to NOINHERIT; verify LOGIN, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION and NOBYPASSRLS for each. Provision and retain a stable NLC_RLS_HMAC_SECRET of at least 32 characters.
4. Actual Render environment confirmation: `APP_DATABASE_URL` must use `nlc_app_role`; `DATABASE_URL` is migration-only; `NLC_RLS_HMAC_SECRET` must match the database key and be present in runtime/migration environments.
5. Post-upgrade forged-identity, signed-user A/B isolation, privilege and policy tests against the actual runtime role.
6. Audited reconciliation of all 85 database rule IDs, including the extra `INC-002`, without unversioned updates.
7. Independent, named, signed Bangladesh-lawyer approval for every applicable rule and separate approval of scoring policy. Until then `approved_rule_ids: []`, `LEGAL_SCORE_RELEASED = False`, and the allowlist remains empty.

**No production migration, role alteration, privilege change, rule-row update, Render deployment or statutory score release has been performed.**
