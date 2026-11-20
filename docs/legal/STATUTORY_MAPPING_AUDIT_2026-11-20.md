# Statutory mapping and product-scoring audit — 20 November 2026

## Scope and authority

Repository baseline reviewed: `main` at `dfdd96fa6fadd48e6080acf1375286ff78113f6b`. This is a first-pass source-backed engineering audit of high-impact Companies Act 1994 (Bangladesh) mappings and the current production scoring data. It is not a completed 85-rule legal opinion, a statutory compliance certificate, or independent counsel approval.

Primary sources checked:

- Bangladesh Laws (official consolidated Companies Act 1994): https://bdlaws.minlaw.gov.bd/act-print-788.html
- Official Companies Act, capital reduction provisions, ss.58–70: https://bdlaws.minlaw.gov.bd/act-788/act-part-print-354.html
- Official Companies Act, management, directors, audit and other provisions: https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html
- Official Companies Act s.210: https://bdlaws.minlaw.gov.bd/act-788/section-33854.html?lang=en
- RJSC eBRS official filing FAQ (Form IX, Form XII, Form XV and filing periods): https://ebrs.roc.gov.bd/public/faqs
- RJSC official Form IX PDF: https://roc.gov.bd/sites/default/files/files/roc.portal.gov.bd/forms/6ad39f2f_1cd0_4910_acce_7f477f3def68/FORM%20IX%20%282%29.pdf

The promulgated Bangla text must be treated as controlling where an English translation differs. Each rule still requires amendment chronology, company-type applicability, Articles review, exceptions, evidence, remedies and counsel disposition.

## Rule mapping checks

| Rule / topic | Candidate statutory mapping | Audit result and required safeguard |
|---|---|---|
| AGM-001 — first AGM | Companies Act s.81(1) | Official Act text permits the first AGM within 18 months after incorporation. Calendar-month arithmetic is preferable to a fixed 548-day shortcut. Check any applicable Registrar extension and the exact incorporation date. |
| AGM-003 / AGM-004 — notice | s.85 | Keep notice-period, service, clear-day calculation and short-notice consent as separate tests. Do not infer defective service from an absent upload. |
| AGM-005 — quorum | s.85(2)(b), read with the Articles | Default quorum is two for a private company with no more than six members, three for a private company with more than six members, and five for other companies. Verify the operative Articles and actual membership/attendance before a breach finding. |
| AGM-006 — minutes | s.89 | Minutes are an internal statutory record. Missing upload is not proof that minutes were never made or maintained. |
| Minimum directors | s.90(1)–(2) | At least three for a public company and a private subsidiary of a public company; at least two for other private companies. Subsidiary classification and actual director status need authoritative evidence. |
| DIR-001 — Form XII | s.115; RJSC Form XII guidance | RJSC eBRS lists Form XII within 14 days after appointment/change. Keep this separate from director consent and internal registers. |
| DIR-007 — director consent | s.93(2), with s.92 / Form IX cross-reference | The Act's s.93(2) sets the 30-day Registrar-filing period after appointment. RJSC labels Form IX under s.92 and its FAQ also describes the 30-day post-appointment filing. Retain both references; do not collapse pre-appointment eligibility/consent and post-appointment Registrar filing into one event. |
| AUD-001 — first auditor | s.210(6) | Official s.210 text requires the Board to appoint the first auditor within one month after registration. Use calendar-month arithmetic. Do not confuse this with s.210(2)'s separate auditor notice duty. |
| CAP-003 — capital reduction | ss.59–60 (and related ss.61–70 as applicable) | A reduction requires constitutional authority, special resolution and court confirmation under the statutory process. A pending workflow alone is not proof of an unlawful completed reduction. |
| REG-002 — internal registers | ss.34, 89, 174 | Distinguish register of members, meeting minutes and register of charges. Director particulars/Form XII are a separate s.115 filing duty, not an inferred internal register. |
| CHG-001 — satisfaction of charge | s.172; creation/registration is separately under s.159 | Satisfaction notice is due within 21 days under s.172. Do not cite s.159 as the satisfaction provision. |
| AR-001 / AR-003 — annual return | s.36 and Schedule X; s.346 is a separate Registrar process | Annual-return duty and strike-off action must not be conflated. A backlog alone does not prove that Registrar proceedings have commenced or that the company is dissolved. |
| DEF-001 — director disqualification | s.94 and the Articles | Require a specific ground, director identity, authoritative evidence, effective date and continuing status. The unpaid-call threshold remains disputed in the source dossier; do not auto-classify it. |

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

## Scoring and legal verification — separate controls

- Product scoring: the engine's `LEGAL_SCORE_RELEASED` switch defaults to true; `PRODUCT_SCORING_RULE_IDS` and `SCORE_DEDUCTION_RULE_IDS` each contain the 85 product-owner-approved rule IDs. Production Render was explicitly set to `LEGAL_SCORE_RELEASED=true` on 20 November 2026 and deployment `dep-dc07cb61egvs7387q090` is confirmed live on SHA `dfdd96fa6fadd48e6080acf1375286ff78113f6b`.
- Independent legal verification: `VERIFIED_RULE_IDS` remains empty. All 85 entries in `docs/legal/legal_approval_register.yaml` remain `REVIEW_REQUIRED / score_eligible: false`. No independent counsel approval is recorded.
- Product scoring is a deterministic NLC risk metric, not a legal opinion, statutory verification or compliance certificate. Deductions must remain gated by confirmed violation, applicability, provenance, evidence sufficiency, state and category caps. `UNKNOWN`, `NOT_EVALUATED`, `DISPUTED` and `REQUIRES_LAWYER_JUDGMENT` must not be treated as compliant or scored as a confirmed violation.

## Production database observations — read-only

Production Neon branch `br-purple-fog-aodj8s04`, database `neondb`, was inspected read-only:

- Alembic revision: `0112_runtime_acl_and_alembic_rls`; migration to 0122 is not complete.
- `legal_rules`: 86 rows, 86 active, 0 marked VERIFIED, 0 catalogue rows with non-zero `score_impact`. The extra row relative to the 85-rule product set requires identity reconciliation; do not force parity with ad hoc inserts/deletes.
- Target company latest stored evaluation: `3150a0df-de28-4dd3-ab97-6bb16e1d7683`, calculated 15 November 2026, catalogue count 86, score 85, risk band RED.
- Its 86 rule outcomes: 77 NOT_EVALUATED, 4 UNKNOWN, 2 NON_COMPLIANT, 3 REQUIRES_LAWYER_JUDGMENT.
- Current active flags: 9 total — 7 UNKNOWN with zero impact; 2 VIOLATION findings (TL-001 impact 5; REG-002 impact 12).
- Score history has only three rows; its newest row is 9 November with null score and `NOT_RELEASED`. The 15 November evaluation is not represented by a matching score-history row. Reconcile this persistence/reporting difference before treating the historical dashboard trend as current.

These are stored database observations, not a fresh authenticated API evaluation. A new evaluation and six-state endpoint response must be generated after migration/deployment and tenant authorization checks.

## Production RLS spot-check — read-only

On the same production branch, the runtime role `nlc_app_role` reported `rolsuper=false` and `rolbypassrls=false`. `neondb_owner` is provider-managed and BYPASSRLS, but it is not the runtime role. RLS is enabled and forced on the inspected tables `companies`, `company_user_access`, `compliance_flags`, `compliance_evaluation_runs`, `compliance_score_history` and `user_activity_logs`. The activity-log table has exactly one policy.

The production `company_user_access` policy inventory still contains `company_user_access_staff_write`; migration 0122 is designed to replace it with `company_user_access_admin_write`. This independently confirms why the current 0112 revision cannot be treated as the final P0 security state. These catalog checks are spot checks, not a full signed-user cross-tenant denial matrix.

## Release disposition

1. Keep product scoring enabled as an explicitly labelled product risk metric.
2. Keep legal verification fail-closed: zero `VERIFIED_RULE_IDS` until actual independent, rule-specific counsel decisions are recorded.
3. Keep all unresolved rule outcomes non-scoring; no default GREEN, no missing-evidence breach and no automatic BLACK from a backlog or allegation.
4. Finish PR #381 (Alembic metadata-only fix) and PR #382 (citation audit correction) with passing CI.
5. Complete migration 0112→0122, verify RLS/tenant isolation and production readiness, then generate a fresh company-specific six-state evaluation and reconcile score history.
6. Complete the remaining 85-rule proposition-by-proposition source and applicability review before making any claim of statutory legal verification.
