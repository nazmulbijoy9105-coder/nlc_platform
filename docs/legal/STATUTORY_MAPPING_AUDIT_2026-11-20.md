# Statutory mapping and product-scoring audit — 20 November 2026

## Scope and authority

Repository baseline reviewed: `main` at `dfdd96fa6fadd48e6080acf1375286ff78113f6b`. This is a first-pass source-backed engineering audit of high-impact Companies Act 1994 (Bangladesh) mappings and the current production scoring data. It is not a completed 85-rule legal opinion, a statutory compliance certificate, or independent counsel approval.

Primary sources checked:

- Bangladesh Laws (official consolidated Companies Act 1994): https://bdlaws.minlaw.gov.bd/act-print-788.html
- Official Companies Act, capital reduction provisions, ss.58–70: https://bdlaws.minlaw.gov.bd/act-788/act-part-print-354.html
- Official Companies Act, management, directors, audit and other provisions: https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html
- Official s.90 minimum director count: https://bdlaws.minlaw.gov.bd/act-788/section-32914.html?lang=bn
- Official s.172 charge-satisfaction filing: https://bdlaws.minlaw.gov.bd/act-788/section-33519.html
- Official Companies Act s.210: https://bdlaws.minlaw.gov.bd/act-788/section-33854.html?lang=en
- RJSC eBRS official filing FAQ (Form IX, Form XII, Form XV and filing periods): https://ebrs.roc.gov.bd/public/faqs
- RJSC official Form IX PDF: https://roc.gov.bd/sites/default/files/files/roc.portal.gov.bd/forms/6ad39f2f_1cd0_4910_acce_7f477f3def68/FORM%20IX%20%282%29.pdf

The promulgated Bangla text must be treated as controlling where an English translation differs. Each rule still requires amendment chronology, company-type applicability, Articles review, exceptions, evidence, remedies and counsel disposition.

## Rule mapping checks

| Rule / topic | Candidate statutory mapping | Audit result and required safeguard |
|---|---|---|
| AGM-001 — first AGM | Companies Act s.81(1) | Official Act text permits the first AGM within 18 months after incorporation. Calendar-month arithmetic is preferable to a fixed 548-day shortcut. Check the exact incorporation date and any valid Registrar order. |
| AGM-002 — subsequent AGM | s.81(1) | The Act also requires an AGM in each English calendar year and limits the interval between AGMs to 15 months; the Registrar may extend a subsequent AGM within the statutory application window, up to the earlier of 90 days or 31 December. The engine has a separate subsequent-AGM deadline helper; verify its inputs include prior AGM date, calendar-year duty and actual Registrar order. |
| AGM-003 / AGM-004 — notice | s.85(1)(a) | The Act text requires at least 21 days' written notice, subject to specified short-notice consent. The service layer derives the notice date only after verifying the member-register snapshot, the complete recipient count and per-member notice evidence; short-notice consent is also verified per entitled member with evidence and reviewer provenance. The engine then compares date difference to 21 days. The remaining legal question is whether the statutory phrase requires a distinct 'clear days' counting convention; keep that interpretation open for primary-authority/counsel review before treating the 21-day calculation as legally verified. |
| AGM-005 — quorum | s.85(2)(b), read with the Articles | Default quorum is two for a private company with no more than six members, three for a private company with more than six members, and five for other companies. Verify the operative Articles and actual membership/attendance before a breach finding. |
| AGM-006 — minutes | s.89 | Minutes are an internal statutory record. Missing upload is not proof that minutes were never made or maintained. |
| Minimum directors | s.90(1)–(2) | At least three for a public company and a private subsidiary of a public company; at least two for other private companies. Subsidiary classification and actual director status need authoritative evidence. |
| DIR-001 — Form XII | s.115(2); RJSC Form XII | The Act itself gives 14 days for first particulars and subsequent changes; current eBRS FAQ also says 14 days. A legacy RJSC portal page says 15 days, which conflicts with the Act/current FAQ and must not override the statutory text. Keep this separate from director consent and internal registers. |
| DIR-007 — director consent | s.93(2), with s.92 / Form IX cross-reference | The Act's s.93(2) sets the 30-day Registrar-filing period after appointment. RJSC labels Form IX under s.92 and its FAQ also describes the 30-day post-appointment filing. Retain both references; do not collapse pre-appointment eligibility/consent and post-appointment Registrar filing into one event. |
| AUD-001 — first auditor | s.210(6) | Official s.210 text requires the Board to appoint the first auditor within one month after registration. Use calendar-month arithmetic. Do not confuse this with s.210(2)'s separate auditor notice duty. |
| CAP-003 — capital reduction | ss.59–60 (and related ss.61–70 as applicable) | A reduction requires constitutional authority, special resolution and court confirmation under the statutory process. A pending workflow alone is not proof of an unlawful completed reduction. |
| REG-002 — internal registers | ss.34, 89, 174 | Distinguish register of members, meeting minutes and register of charges. Director particulars/Form XII are a separate s.115 filing duty, not an inferred internal register. |
| CHG-001 — satisfaction of charge | s.172(1), read with s.159; creation/registration is separately under s.159 | The official Act text at s.172(1) requires notice within 21 days after satisfaction of a registrable charge. The RJSC eBRS FAQ lists Form XXVIII with ss.12/391, which conflicts with the Act section text; keep s.172 as the statutory anchor and record the form cross-reference discrepancy for counsel/RJSC confirmation. Do not cite s.159 alone as the satisfaction provision. |
| AR-001 / AR-003 — annual return | s.36 and Schedule X; s.346 is a separate Registrar process | Annual-return duty and strike-off action must not be conflated. A backlog alone does not prove that Registrar proceedings have commenced or that the company is dissolved. |
| DEF-001 — director disqualification | s.94 and the Articles | Require a specific ground, director identity, authoritative evidence, effective date and continuing status. The unpaid-call threshold remains disputed in the source dossier; do not auto-classify it. |

## Historical source-triage discrepancies found against current runtime declarations

A comparison of the 6 November 85-rule source-triage table with the current runtime declarations found that several old candidate anchors were superseded by later engineering corrections. These are not counsel approvals; they are source-mapping corrections or review flags:

| Rule | Older triage anchor | Current runtime anchor / disposition |
|---|---|---|
| INC-004 | s.53 | s.56 is cited for the increase-in-registered-capital filing trigger; confirm the exact capital transaction before applying. |
| AUD-003 | ss.151, 210 | ss.183 and 210; s.151 is return of allotment and must not anchor audited-accounts findings. |
| AUD-004 | s.210(2) | s.210(3) is the current retiring-auditor reappointment anchor; s.210(2) is a separate notice duty. |
| DIR-001 | s.90 | s.115(2) / Form XII filing; s.90 concerns minimum director count. |
| DIR-004 | s.109 | s.115 / director particulars; cessation filing is not the s.109 managing-director restriction. |
| DIR-007 | s.92 only | s.93(2) for the 30-day Registrar filing period, with s.92/Form IX cross-reference. |
| CAP-001 | s.53 only | ss.53, 54 and 56; the trigger must distinguish capital alteration type and filing duty. |
| BNK-001 | Bankruptcy Act 1997 s.12 | Companies Act 1994 Part V, including ss.241–244; exact petition ground is case-specific. |
| BNK-002 | Bankruptcy Act 1997 s.14 | Companies Act 1994 Part V; s.255 applies to court-appointed Official Liquidators, and voluntary appointment is route-specific. |
| BNK-003 | Bankruptcy Act 1997 s.18 | Companies Act 1994 Part V, including ss.241–246; require the operative court order. |
| ESC-001 | s.304 | s.346; require authenticated Registrar process, not a return-backlog heuristic. |
| ESC-004 | s.130 | s.286 and following provisions for voluntary winding-up; verify the actual resolution/route. |
| ESC-005 | s.104 | ss.195, 197 and, where related entities are included, s.199; require the relevant investigation/order. |
| REG-001 | s.34 | Current engine rule is a generic internal-register completeness signal with no single statutory basis. Split by register type before treating it as a statutory finding. |

Additional current runtime rules intentionally remain without a single universal section anchor: DIR-002, DIR-006, DEF-002, BSEC-001 and VAT-003. FX-001, BSEC-002–004, TAX-001–004, VAT-002, LBR-001–003 and TL-001–002 require exact instrument, amendment, company/taxpayer class or local-authority scope review. ESC-003 is NLC internal risk policy, not a statutory breach. None of these unresolved anchors should be converted into an adverse statutory finding by default.

## Audit-tool correction

The former `tools/legal_citation_audit.py` contained stale expectations that could incorrectly flag the corrected runtime mappings. The following anchors were updated in PR #382:

- DIR-001 / DIR-002: s.115, not s.90 / s.93.
- DIR-004: s.115 (director cessation particulars/Form XII), not ss.109–110.
- DIR-007: s.93(2) plus s.92 / Form IX cross-reference.
- REG-002: ss.34, 89 and 174.
- CAP-001: ss.53, 54 and 56; the rule is an internal review signal, not a blanket special-resolution breach.
- CAP-003: ss.59–60, not s.150.
- CHG-001: s.172, not s.159.
- DEF-001: s.94, not ss.118(6) / 182(9).
- AGM-005: s.85(2)(b); AGM-006: s.89.

The audit script is a citation-anchor consistency check only. It does not establish that every element of a rule proposition is legally correct. CI reports unmapped IDs as warnings; those warnings are an explicit remaining worklist, not passed legal mappings. REG-001 is intentionally left without a single statutory anchor because it aggregates multiple register duties; split and map each register type before enabling any rule-specific adverse finding.

The latest CI audit run (`44775805744`) returned `0 FAIL / 63 WARN / 52 PASS`. The 63 warnings span 54 rule IDs whose expected source anchors are not yet fully pinned in the audit harness: `INC-003`, `INC-004`, `INC-005`, `INC-006`, `INC-007`, `AUD-003`, `AUD-004`, `AGM-003`, `AGM-004`, `AR-002`, `AR-003`, `AR-004`, `DIR-003`, `SH-003`, `TR-002`, `TR-003`, `TR-004`, `TR-005`, `TR-006`, `REG-001`, `REG-003`, `CAP-004`, `TAX-001`, `TAX-002`, `TAX-003`, `TAX-004`, `VAT-002`, `VAT-003`, `DEF-002`, `STR-001`, `STR-002`, `STR-003`, `BNK-001`, `BNK-002`, `BNK-003`, `LBR-003`, `LBR-001`, `LBR-002`, `AGM-007`, `DIR-005`, `DIR-006`, `ESC-004`, `ESC-005`, `DIR-008`, `DIR-010`, `FX-001`, `BOD-001`, `BOD-002`, `BOD-003`, `ACC-001`, `ACC-003`, `ESC-001`, `ESC-002`, `ESC-003`. These are not legal pass results; they require source-anchor pinning and proposition-level review.

## Scoring and legal verification — separate controls

- Product scoring: the engine's `LEGAL_SCORE_RELEASED` switch defaults to true; `PRODUCT_SCORING_RULE_IDS` and `SCORE_DEDUCTION_RULE_IDS` each contain the 85 product-owner-approved rule IDs. Production Render was explicitly set to `LEGAL_SCORE_RELEASED=true` on 20 November 2026 and deployment `dep-dc07cb61egvs7387q090` is confirmed live on SHA `dfdd96fa6fadd48e6080acf1375286ff78113f6b`.
- Independent legal verification: `VERIFIED_RULE_IDS` remains empty. All 85 entries in `docs/legal/legal_approval_register.yaml` remain `REVIEW_REQUIRED / score_eligible: false`. No independent counsel approval is recorded.
- Product scoring is a deterministic NLC risk metric, not a legal opinion, statutory verification or compliance certificate. Deductions must remain gated by confirmed violation, applicability, provenance, evidence sufficiency, state and category caps. `UNKNOWN`, `NOT_EVALUATED`, `DISPUTED` and `REQUIRES_LAWYER_JUDGMENT` must not be treated as compliant or scored as a confirmed violation.

## Production database observations — read-only

Production Neon branch `br-purple-fog-aodj8s04`, database `neondb`, was inspected read-only:

- Alembic revision: `0122_rls_staff_scope_and_score_history` is now applied to production. The migration workflow's follow-up `alembic current` check failed because the pooled connection returned the exact migration login with the owner role already active; the Render deploy hook was skipped. PR #383 fixes the idempotent role preflight and resets the role between Alembic processes.
- `legal_rules`: 86 rows, 86 active, 0 marked VERIFIED, 0 catalogue rows with non-zero `score_impact`. The extra row relative to the 85-rule product set requires identity reconciliation; do not force parity with ad hoc inserts/deletes.
- Target company latest stored evaluation: `3150a0df-de28-4dd3-ab97-6bb16e1d7683`, calculated 15 November 2026, catalogue count 86, score 85, risk band RED.
- Its 86 rule outcomes: 77 NOT_EVALUATED, 4 UNKNOWN, 2 NON_COMPLIANT, 3 REQUIRES_LAWYER_JUDGMENT.
- Current active flags: 9 total — 7 UNKNOWN with zero impact; 2 VIOLATION findings (TL-001 impact 5; REG-002 impact 12).
- Score history has only three rows; its newest row is 9 November with null score and `NOT_RELEASED`. The 15 November evaluation is not represented by a matching score-history row. Reconcile this persistence/reporting difference before treating the historical dashboard trend as current.

Post-migration row counts are 549 compliance flags, 74 score-history rows, 175 evaluation runs and 86 legal-rule rows. The canonical identity registry contains 85 identities and 85 unresolved aliases (0 resolved); historical finding bindings, finding-evidence links, finding contexts and rescue-audit rows remain 0. This is a fail-closed, no-backfill posture, but it means old findings still lack canonical rule/evidence binding. These are stored database observations, not a fresh authenticated API evaluation. A new evaluation and six-state endpoint response must be generated after migration/deployment and tenant authorization checks.

The main CI static coverage artifact (run `44774872530`) reports 85 registered and 85 implemented rules, but active, applicable and evaluated counts are explicitly `not collected`; it is not a live six-state company report. The production endpoint is `GET /api/v1/companies/{company_id}/rule-coverage` and requires a signed user with company access. No authenticated production response was available during this audit, so the live six-state endpoint remains unverified.

## Production RLS spot-check — read-only

On the same production branch, the runtime role `nlc_app_role` reported `rolsuper=false` and `rolbypassrls=false`. `neondb_owner` is provider-managed and BYPASSRLS, but it is not the runtime role. RLS is enabled and forced on the inspected tables `companies`, `company_user_access`, `compliance_flags`, `compliance_evaluation_runs`, `compliance_score_history` and `user_activity_logs`. The activity-log table has exactly one policy.

Post-migration policy inventory now shows `company_user_access_admin_write` and `company_user_access_scoped_read`; the former `company_user_access_staff_write` policy is absent. `compliance_score_history` has only tenant-scoped INSERT and SELECT policies; `user_activity_logs` still has exactly one actor/tenant policy. These catalog checks are spot checks, not a full signed-user cross-tenant denial matrix.

## Release disposition

1. Keep product scoring enabled as an explicitly labelled product risk metric.
2. Keep legal verification fail-closed: zero `VERIFIED_RULE_IDS` until actual independent, rule-specific counsel decisions are recorded.
3. Keep all unresolved rule outcomes non-scoring; no default GREEN, no missing-evidence breach and no automatic BLACK from a backlog or allegation.
4. Finish PR #381 (Alembic metadata-only fix) and PR #382 (citation audit correction) with passing CI.
5. Complete migration 0112→0122, verify RLS/tenant isolation and production readiness, then generate a fresh company-specific six-state evaluation and reconcile score history.
6. Complete the remaining 85-rule proposition-by-proposition source and applicability review before making any claim of statutory legal verification.


## 21 November 2026 — production re-audit addendum

This addendum supersedes earlier point-in-time counts where they differ. All production queries below were read-only.

### Legal catalogue and canonical identity

- `legal_rules`: 86 rows; 84 active; 2 inactive; 86 PENDING; 0 VERIFIED; 0 catalogue rows with non-zero `score_impact`.
- Inactive rows: `INC-001` (quarantined canonical identity) and `INC-002` (extra inactive historical/duplicate identity). Do not delete or reactivate either row to force count parity.
- The canonical application registry remains 85 IDs. The six-state report should distinguish 85 registered, 85 implemented and 84 active; the extra inactive `INC-002` is not a canonical rule.
- `legal_rule_aliases`: 85 rows; 0 RESOLVED; 85 UNRESOLVED. All 85 have a mapping-basis note, but 0 have an evidence reference. Do not resolve aliases from name similarity or mapping notes alone.
- `compliance_finding_bindings`, `compliance_finding_evidence` and `legal_rule_finding_contexts`: 0 rows. Historical findings therefore remain unbound to authenticated rule revisions and evidence manifests.

### Historical evaluation and score history

The selected production evaluation is run `3150a0df-de28-4dd3-ab97-6bb16e1d7683`, calculated 15 November 2026 at 05:43:57 UTC:

- Stored status `COMPLETED`; product score 85; risk band RED; engine 2.2; catalogue count 86; outcome count 86.
- Outcomes: 77 `NOT_EVALUATED`, 4 `UNKNOWN`, 2 `NON_COMPLIANT`, 3 `REQUIRES_LAWYER_JUDGMENT`.
- None of the 86 legacy outcome objects contains an `applicability_state` key. The absence must be represented as `UNKNOWN`; it must never be inferred from the outcome state.
- The company has three monthly score-history rows; the newest is 9 November 2026, `NOT_RELEASED`, with a null score. The 15 November per-run evaluation is not a monthly snapshot.

The monthly score-history table is append-only and unique by company/month. Do not overwrite the 9 November `NOT_RELEASED` row with the later evaluation. PR #391 introduces a separate tenant-scoped per-run history endpoint and explicitly defaults legacy missing applicability to `UNKNOWN`; the frontend follow-up displays monthly snapshots and per-run evaluations separately.

### Production RLS negative checks

Using the production runtime role `nlc_app_role`:

- `rolsuper=false`, `rolbypassrls=false`, `rolcreatedb=false`, `rolcreaterole=false`, `rolreplication=false`.
- RLS is enabled and forced on `companies`, `company_user_access`, `compliance_flags`, `compliance_evaluation_runs`, `compliance_score_history` and `user_activity_logs`.
- With no signed context, the runtime role sees zero companies and `nlc_current_user_principal()` returns NULL.
- A fabricated UUID plus invalid signature returns NULL principal and zero visible companies.
- The literal `ADMIN` sentinel plus invalid signature also returns NULL principal and zero visible companies.
- The runtime role is denied access to `alembic_version`, consistent with keeping migration metadata outside ordinary application privileges.

These are production negative/least-privilege checks. They do not replace a positive signed-user production matrix; the manual GET-only workflow in PR #392 requires dedicated client, legal-staff and super-admin test tokens.

### Candidate-anchor audit disposition

The earlier citation-audit output reported unmapped candidate anchors across 54 rule IDs. The updated audit harness now separates:
- candidate-anchor consistency checks;
- explicitly documented review-only propositions (including REG-001, REG-003, DEF-002, BNK-001..003, AGM-007, DIR-005/006 and ESC-003);
- instruments requiring a separate statute-specific audit.

This is a technical traceability correction, not source authentication. A candidate string in engine code is not proof that the provision is current, operative or applicable. The independent counsel register remains 85 `REVIEW_REQUIRED`, `VERIFIED_RULE_IDS` remains empty, and no rule is promoted by this audit.

REG-003 is expressly unresolved: Companies Act section 34(2) is not accepted as a registered-office-location authority. The engine/seed candidate basis is now recorded as an unresolved location proposition; no breach may be inferred pending primary-source and counsel review.

### Deployment alignment and release hold

At this audit point, Render's live backend commit remains `d86784cd3ee0eaa3de32885dba16bf9314c631da`, while GitHub `main` is `c45d368b6c3287f38b71ddf5aceb0ab45ce6fa65`. Render auto-deploy is disabled. Do not trigger production deployment until the approved main commit has passed all required CI, the live signed-user smoke workflow has passed, and the frontend preview/deployment is verified against the matching backend API.
