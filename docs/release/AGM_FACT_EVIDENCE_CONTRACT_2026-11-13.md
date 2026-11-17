# AGM evaluator evidence contract — 13 November 2026

## Release boundary

This contract maps the facts required by AGM-001 through AGM-006 to evidence that can actually establish them. A user-entered value, missing upload, database default, or AI-generated summary is not proof. Each item must retain the original evidence reference, verification actor, verification timestamp, tenant/company binding, and the source/version used to interpret it.

No rule is activated by this document. It does not authorize seed-to-database writes, score changes, statutory conclusions, or calendar-event persistence. The Companies Act source-review batch remains a workpaper pending independent Bangladesh-qualified counsel approval.

## Fact-to-evidence mapping

| Rule / required fact | Acceptable evidence source | Required verification | Unknown / fail-closed treatment |
|---|---|---|---|
| AGM-001 incorporation date | RJSC certificate of incorporation or authenticated RJSC company extract | Match company identity and registration number; retain certified document or official lookup reference and effective date | Missing/unmatched source = UNKNOWN; do not infer incorporation date from customer text |
| AGM-001 / AGM-002 complete AGM history and count | AGM minute books/resolutions, annual returns, RJSC filings and certified company records reconciled into a dated event ledger | Verify all years in scope, duplicate/cancelled events and last AGM date; reviewer + timestamp + source references | Incomplete history = UNKNOWN; never infer zero AGMs from no upload |
| AGM-001 first AGM due date | Verified incorporation date plus source-versioned s.81 rule | Calendar-month arithmetic; preserve trigger and calculation trace | No date if trigger unverified or source rule not approved |
| AGM-002 subsequent AGM due date | Verified last AGM event and complete AGM history | Apply calendar-year and 15-calendar-month tests; preserve first-AGM proviso and Registrar extension evidence | Missing AGM date/history or unverified extension = UNKNOWN / review; no automatic overdue score |
| AGM-002 Registrar extension | Registrar's written order and proof of application date/receipt | Confirm application timing, grant, covered AGM and statutory cap against effective version of s.81 | Customer assertion or application alone is not a grant; unsupported extension = UNKNOWN |
| AGM-003 / AGM-004 entitled member roster | Dated register of members and Articles determining voting entitlement | Reconcile roster to the meeting date; verify every entitled member and total count | Incomplete roster = UNKNOWN; do not infer consent from missing rows |
| AGM-003 / AGM-004 notice dispatch/service | Notice copy plus postal/courier receipts, email delivery logs or other legally accepted service evidence; per-member records | Verify meeting date, dispatch date, recipient entitlement and service status; retain original dispatch evidence | No proof of dispatch/service = UNKNOWN, not automatically proof of non-service |
| AGM-003 short-notice consent | Separate written consent from every member entitled to attend and vote, tied to the exact meeting | Verify identity, entitlement, consent wording, date and authenticity for each entitled member | Any missing/ambiguous consent = UNKNOWN; verified non-consent can support a notice-defect finding subject to counsel-approved interpretation |
| AGM-003 / AGM-004 accidental omission or non-receipt | Member-specific notice register plus contemporaneous evidence explaining the omission/non-receipt and verification record | Distinguish accidental omission/non-receipt from deliberate non-service; preserve the specific member and meeting | Unverified accidental characterisation is not an exception; do not treat a bare flag as proof |
| AGM-005 Articles-based quorum | Certified/current Articles and all amendments effective on meeting date; exact quorum clause | Reviewer identifies operative clause, effective date, member class and whether statutory default is displaced | Missing/uncertain Articles = UNKNOWN; do not apply statutory default as if Articles were checked |
| AGM-005 statutory default quorum | Verified company type and member count on meeting date, plus controlling s.85(2)(b) version | Calculate private-company tiers (up to six / more than six) or applicable other-company threshold; record why default applies | Unverified company type/member count = UNKNOWN |
| AGM-005 attendance | Signed attendance register, minutes and/or authenticated meeting records | Reconcile actual persons present with entitled-member roster and personal-presence requirement | Attendance unverified = UNKNOWN; no quorum failure conclusion |
| AGM-006 minutes prepared/entered | Original minute book or authenticated extract, signed minutes and meeting record | Verify entry, date, signatures and custody; distinguish preparation from mere upload | Missing upload alone is not proof minutes do not exist |
| All AGM rules — company identity and provenance | Tenant-bound company registry identity plus immutable evidence metadata | Bind every fact to company_id, source hash/reference, verifier identity and verification time | Cross-tenant/unbound evidence is rejected; stale/conflicting evidence becomes UNKNOWN or DISPUTED |

## Evaluator contract

1. Every fact has three distinct states: verified true, verified false, and unknown. Null/missing evidence is never converted to false.
2. UNKNOWN, DISPUTED, CONTRADICTORY, NOT_APPLICABLE, and REQUIRES_LAWYER_JUDGMENT produce zero statutory score impact.
3. A deadline requires an approved source/version, in-force effective interval, verified trigger fact, verified applicability, and an explicit calculation convention. No customer calendar event is emitted from a preview candidate.
4. Notice consent is evaluated against the complete entitled-member roster. A partial roster cannot establish unanimous consent or its absence.
5. An accidental-omission exception is member-specific and requires contemporaneous evidence plus independent verification.
6. Quorum is not computed from member count alone where the Articles may prescribe another rule. The operative Articles clause must be reviewed and evidenced.
7. The source register must store the exact provision/subsection, source URL or certified copy reference, source language, amendment chain, effective interval, retrieval date, reviewer, and counsel approval record.
8. Product-owner approval is separate from legal approval. Neither approval is inferred from a CI pass, migration, or metadata match.

## Required source review still open

The Companies Act source-review batch 1 records the initial evidence and its limitations. Before implementation, obtain and reconcile the official consolidated Act/Gazette text and amendments for each proposition, including s.81, s.85 and s.89. Confirm the exact counting convention and exceptions with Bangladesh-qualified company-law counsel. RJSC FAQs and professional manuals are corroborative, not substitutes for the Act.

## Release gate

Keep the registry PENDING / NOT_EVALUATED, score impact zero, BLACK override false, and customer calendar generation disabled until all of the following exist: rule-specific source approval, rule-specific evidence contract, tested evaluator semantics, product-owner decision, counsel sign-off, release-bound migration, parity verification and production rollback evidence.
