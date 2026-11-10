# Continuous compliance vertical slice: AGM, annual return and auditor

## Product rule

NLC is a continuous company-secretarial workspace. A score is a derived operational
summary; the primary records are company facts, legal obligations, evidence, deadlines,
filings, legal changes and remediation actions.

This delivery is intentionally a vertical-slice contract, not a 14-domain catalogue.
The first slice is limited to AGM, annual return and auditor appointment.

## Three orthogonal state dimensions

Every obligation instance stores three independent dimensions:

| Dimension | Values |
|---|---|
| Applicability | APPLIES, DOES_NOT_APPLY, UNKNOWN |
| Evidence | VERIFIED_PRESENT, VERIFIED_ABSENT, NOT_PROVIDED, CONFLICTING |
| Status | NOT_YET_DUE, DUE_SOON, COMPLIANT, FILED_LATE, OVERDUE, DISPUTED, WAIVED, EXEMPTED |

NOT_APPLICABLE is not a compliance status. It is represented by
applicability=DOES_NOT_APPLY. For waived or exempted obligations, preserve the
applicability decision and the separate waiver/exemption basis.

VERIFIED_ABSENT means a particular record was not found in a named source on a
recorded date. It does not, by itself, establish that the statutory act never occurred
or that the obligation was breached.

FILED_LATE requires a verified filing receipt/date later than the applicable statutory
deadline. It is a cured filing state and may retain penalty exposure. It is neither
COMPLIANT (on time) nor OVERDUE (still unfiled).

## Fact provenance and applicability work

Every fact used by an assessment carries one of these trust levels:
USER_ASSERTED, DOCUMENT_BACKED, RJSC_CONFIRMED. Findings retain the fact keys,
source references, trust level and observation date. User-asserted facts remain visible
as unverified inputs; they cannot silently become RJSC-confirmed.

Every UNKNOWN applicability state creates a resolution task with an owner, due date,
questionnaire key, document-request key and escalation interval. The default task
deadline is 14 days, configurable by product policy. A dashboard reports resolved
versus unresolved applicability coverage beside—not inside—the score.

For operating companies, recording active operations or employees should set relevant
tax/VAT/trade-licence/labour applicability to APPLIES_PENDING_CONFIRMATION at the
workflow layer. This is a confirmation task, not a legal conclusion or breach. BSEC
and sector-specific applicability remains UNKNOWN until company facts identify the
relevant activity or issuer status.

## Law in force and immutable assessment snapshots

Every legal rule version has a stable rule ID and rule version, catalogue version,
statutory citation and source reference, effective_from and exclusive effective_to
dates, and reviewer/approval metadata using the existing LegalRule verification fields.

A rule can generate a finding only when the existing legal-rule verification gate
reports VERIFIED and includes verified_by and verified_at. Do not create a parallel
approval mechanism. Findings pin the exact rule version, catalogue version and
relevant legal date. Historical assessment selects the rule version in force on the
legally relevant date, not today's rule version.

No section, deadline, exemption, Finance Act, SRO or RJSC circular should be marked
approved merely because it appears in this design. Legal sources and effective dates
must be populated and reviewed through the existing governance workflow before
production findings are enabled.

## Vertical-slice lifecycle

1. Capture incorporation date, company type, one-person/small-company facts where
   relevant, financial year, AGM history, auditor appointment and annual-return history.
2. Attach provenance to every fact: user assertion, uploaded document, or RJSC-
   confirmed source. Record source and observation date.
3. Resolve applicability. Unknowns create owned questionnaire/document tasks with
   expiry and escalation. Do not turn unknown into absence or breach.
4. Select the rule version effective on the relevant legal date and require the
   existing VERIFIED rule gate.
5. Generate one obligation instance per legal event/period. AGM, annual return and
   auditor appointment remain separate obligations with distinct trigger/deadline
   calculations.
6. Reconcile evidence. A verified late receipt produces FILED_LATE; a missing upload
   alone produces NOT_PROVIDED; a verified source search records VERIFIED_ABSENT
   with source/date.
7. Create one remediation record per actionable finding, or an explicit no-action
   disposition with reason. Preserve owner, required documents, dependencies,
   internal target, statutory deadline, filing fees/costs, completion evidence and
   reviewer.
8. Reassess from event/evidence history. Never overwrite the original assessment
   snapshot or its law/catalogue version.

## Scope exclusions

- Winding-up is a lifecycle event that suspends or replaces ordinary obligations,
  not a routine obligation domain.
- One-person companies and small-company exemptions require explicit applicability
  rules before application.
- Beneficial ownership is excluded until the exact source instrument, scope and
  effective date are identified and approved through the existing reviewer gate.
- BSEC and sector rules are not applied to every private company.
- This slice does not assert a live RJSC integration. RJSC-confirmed means an
  authenticated source/receipt was checked and provenance recorded; manual uploads
  remain document-backed unless independently confirmed.

## Acceptance criteria

- APPLIES + NOT_PROVIDED + OVERDUE is representable.
- FILED_LATE requires verified evidence and a date after the deadline.
- VERIFIED_ABSENT requires a named source and check date.
- Each fact carries trust level, source reference and observation date.
- Unknown applicability has owner, deadline, questionnaire and document request.
- Each finding pins legal date, rule version and catalogue version.
- PENDING/DISPUTED rules cannot generate approved legal findings.
- A late filing is cured with penalty exposure, not still overdue.
- AGM, annual return and auditor appointment are independent obligations.
- Applicability coverage is separate from the compliance score.
