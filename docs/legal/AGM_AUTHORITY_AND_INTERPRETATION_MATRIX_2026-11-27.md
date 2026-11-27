# AGM statutory authority and interpretation matrix

**Status:** Engineering authority register; not a legal opinion or counsel approval  
**Prepared:** 27 November 2026  
**Scope:** AGM-001 first AGM, adjacent AGM-002 boundary, court/Registrar orders, and scoring interpretation  
**Baseline branch:** `test/agm001-deterministic-deadlines-20261127`

## 1. Governance and use

This matrix separates (a) statutory text, (b) NLC's present implementation, (c) product-risk policy, and (d) questions requiring a Bangladesh-qualified company-law reviewer. A source link or engineering test is not legal approval. The official Bangla text is controlling where a translation differs. Before release, counsel must confirm the current consolidated text, amendment history, effective date for the relevant company/event, company type, Articles, and any operative order.

No item in this matrix records independent counsel approval. The NLC legal approval register remains the source of truth for approval status; an engineering PR must not change `VERIFIED_RULE_IDS` or mark an AGM rule legally verified.

## 2. Primary authority register

| ID | Official authority | Proposition relevant to AGM | NLC treatment / status |
|---|---|---|---|
| A-01 | [Companies Act 1994 (Bangladesh), s.81(1), official consolidated text](https://bdlaws.minlaw.gov.bd/act-print-788.html) | Annual general meeting duty; first AGM within 18 months after incorporation; annual calendar-year requirement and no more than 15 months between successive AGMs; statutory proviso concerning the year of incorporation and following year where first AGM is held within 18 months. Registrar extension language is part of the same section and must be applied only on evidence of the actual order and statutory conditions. | Primary anchor for AGM-001 and AGM-002. The first-AGM proviso must not be casually generalized into a blanket suspension of every later-AGM requirement. |
| A-02 | [Companies Act 1994, s.82, official consolidated Act](https://bdlaws.minlaw.gov.bd/act-print-788.html) | Statutory consequences/penalty provision associated with default in holding an AGM. | Keep statutory liability separate from NLC's RED/BLACK bands and graduated deduction schedule. Confirm exact current text and responsible-person scope before legal advice or external representation. |
| A-03 | [Companies Act 1994, s.85, official section text](https://bdlaws.minlaw.gov.bd/act-print-788/section-print-32909.html) | Meeting notice, short-notice consent, and court-related meeting provisions. The official consolidated text must be read as a whole; the notice period currently mapped by NLC is 21 days, subject to statutory exceptions. | Not an alternative first-AGM deadline. Any court intervention or short-notice consent requires its own event-specific evidence and reviewer disposition. |
| A-04 | [General Clauses Act 1897, s.3(33), official consolidated text](https://bdlaws.minlaw.gov.bd/act-print-73.html) and [s.4(1)](https://bdlaws.minlaw.gov.bd/act-print-73.html) | “Month” is defined by reference to a month reckoned according to the British calendar; the interpretation provisions apply subject to contrary intention/context. | Supports calendar-month rather than fixed-day arithmetic. It does not, without further analysis, settle every month-end clamping or inclusive/exclusive counting question. |
| A-05 | [Companies Act 1994, s.24, official consolidated Act](https://bdlaws.minlaw.gov.bd/act-print-788.html) | Incorporation/registration certificate and its evidential role. | Verify the actual certificate and legally operative registration/incorporation date; do not substitute an application, name-clearance, or commencement date. Counsel to confirm exact s.24(2) proposition and date effect. |

**Source caveat:** These are official Bangladesh Laws consolidated pages. Record the accessed version/date and inspect the promulgated Bangla text and amendment history when the matrix is used for a live company decision. URLs alone do not prove the version applicable to a historical event.

## 3. Rule-level mapping and current implementation

| Rule / issue | Statutory proposition | Current NLC implementation | Boundary / control |
|---|---|---|---|
| AGM-001 — first AGM | First AGM within 18 months after incorporation under s.81(1), subject to the statutory proviso. | Deterministic calendar-month calculation from verified incorporation date; AGM-001 is first-AGM-only and is considered only when AGM history is verified and `agm_count == 0`. | Do not run AGM-001 when count is one or more, or infer a zero count from missing history. Missing/unverified history remains UNKNOWN / NOT_EVALUATED and zero impact. |
| AGM-002 — subsequent AGMs | Each Gregorian calendar year and no more than 15 months between successive AGMs, subject to the statutory proviso and any valid Registrar extension. | Separate subsequent-AGM helper using verified AGM history. | Keep independent from AGM-001. Do not change its deadline based on an assumed reading of the first-AGM proviso; see open issue L-02. |
| Month arithmetic | “Month” has a statutory calendar meaning under the General Clauses Act. | Calendar-month arithmetic is used rather than a hard-coded 548-day period. | Month-end clamping (e.g. 31 August + 18 months → last day of February) is an implementation convention pending counsel confirmation, not a proposition conclusively established by s.3(33) alone. |
| Registrar extension | Section 81 contains a limited extension mechanism with statutory prerequisites and time limits. | A claimed extension must be tied to the actual Registrar order and its terms. | Do not infer extension from an application, email, pending request, or generic grace period. Preserve order scope, date, period, conditions, and verification. |
| Court order / directions | The legal effect depends on the precise statutory power invoked, operative wording, parties, event, period, and subsequent orders. | No order automatically changes a rule outcome or clears a breach. Potentially relevant order is routed to lawyer judgment until reviewed. | See L-01. Distinguish a court-convened meeting, extension/relief, stay, direction, and post-default consequence; do not treat them as interchangeable. |

## 4. Unresolved legal interpretations — decision register

All entries below are **OPEN / NOT COUNSEL-APPROVED**. They are intentionally not resolved by code.

| ID | Question requiring legal decision | Why it matters | Interim fail-closed product treatment | Required approver / evidence |
|---|---|---|---|---|
| L-01 | What legal effect, if any, does a court order or direction have on an AGM deadline, an existing default, a proposed meeting, or consequences of default? Identify the exact statutory source and distinguish s.81 Registrar extension from any court power under s.85 or other provision. | A court order may be narrow, conditional, stayed, superseded, or directed to a different event/company. | Preserve order evidence; route to `REQUIRES_LAWYER_JUDGMENT`; no automatic compliance, breach clearance, score uplift, or BLACK override. | Bangladesh-qualified company-law counsel; authenticated/certified order, case number, court, operative paragraphs, service/knowledge, appeal/stay/superseding order, event linkage. |
| L-02 | How does the first-AGM proviso in s.81(1) interact with the annual calendar-year duty and 15-month interval for the next AGM after a first AGM held early or late within the 18-month period? | Current engine and service helper can diverge in boundary scenarios; the statutory text may support competing readings. | Do not modify AGM-002 from an assumed interpretation. Disputed or affected schedule remains review-only / NOT_EVALUATED. | Written counsel opinion addressing the statutory text and worked dates; confirm any relevant case law or Registrar practice. |
| L-03 | Does “18 months after incorporation” use the anniversary date with a day-of-month convention, and how should a target month lacking that day be treated? | Month-end clamping can move a calculated deadline and change a boundary outcome. | Keep tested calendar-month/clamp convention as current implementation only; label interpretation unapproved; no representation that this is settled law. | Counsel to specify start-day inclusion, due-day inclusion, missing-day handling, leap-year treatment, and source authority. |
| L-04 | What is the legally operative incorporation/registration date for s.81 where certificate issue, registration entry, or other dates differ? | A one-day source-date error changes the deadline. | Require certificate-backed, verified date; conflicting dates remain UNKNOWN / lawyer review. | Certificate under s.24, registry evidence, amendments/corrections, counsel confirmation of legal effect. |
| L-05 | What evidence proves a first AGM was held, and how should a late-held first AGM affect historical default, current status, and subsequent AGM scheduling? | A current `agm_count > 0` can make AGM-001 no longer applicable even though the meeting may have occurred late. | Capture the event and provenance separately; do not infer historical compliance or erase a historical default until interpretation is approved. | Notice, minutes, attendance, resolutions, statutory books, filings/receipts, date verification, counsel decision. |
| L-06 | What counting convention applies to the 21-day notice period in s.85, including whether “clear days” is required and how service methods affect the date? | Could alter AGM notice validity, but is distinct from the first-AGM deadline. | Keep notice finding separate and review-only where counting/service is disputed. | Counsel opinion on statutory wording, General Clauses Act, service proof and Articles. |

## 5. Product scoring policy — not statutory consequence

The following are NLC product-policy choices, not penalties enacted by the Companies Act:

- Graduated AGM deductions currently use delay bands (5 / 10 / 15 / 20 points).
- The product's RED/BLACK classification, including any 365/366-day boundary, is a risk-severity heuristic.
- A deduction, risk band, rescue trigger, or dashboard label must not be described as the statutory penalty or a judicial finding.
- Only a confirmed, applicable and sufficiently evidenced violation may enter ordinary adverse scoring under the existing product controls.
- `UNKNOWN`, `NOT_EVALUATED`, `DISPUTED`, `CONTRADICTORY`, and `REQUIRES_LAWYER_JUDGMENT` must not silently become compliant or a confirmed violation; they carry zero score impact and no BLACK override.
- Evidence of a meeting, court order, or claimed extension must not improve the score until its authenticity, scope, legal effect, and event linkage have been verified and the required legal decision recorded.
- A score release gate and independent legal-verification allowlist remain separate controls. This document does not authorize changing either.

## 6. Implementation guardrails for the next workstreams

### B — court-order evidence and lawyer-judgment routing

1. Store the order as evidence, not as an automatic rule override.
2. Link it to company, case, court, order date, operative text/paragraphs, affected AGM event, statutory power claimed, and source/certification details.
3. Track verification, reviewer identity/time, appeal, stay, variation, discharge, and superseding order where supported.
4. Until a qualified reviewer records a reasoned decision, route the affected outcome to `REQUIRES_LAWYER_JUDGMENT`, UNKNOWN/NOT_EVALUATED, zero impact, no score uplift, and no BLACK override.
5. A lawyer decision must be attributable, versioned, scoped to the specific event and effective period, and auditable. It must not be a generic “mark compliant” switch.

### C — first-AGM evidence and scoring integration

1. Capture the actual first AGM date with source, provenance, verification status and event/company linkage.
2. Preserve the distinction between “meeting occurred”, “meeting occurred by the deadline”, and “legal effect on later AGM schedule”.
3. A verified date alone is not authority to rewrite AGM-002 or erase a historical default.
4. Score only under a separately recorded, approved interpretation. If counsel approval is absent or the date/meaning is disputed, retain UNKNOWN/NOT_EVALUATED and zero impact.
5. Test on-time, late, boundary, missing, conflicting, unverified, and superseded evidence cases; verify score hash/provenance and ensure evidence injection cannot silently improve the score.

## 7. Change control and approval record

| Field | Value |
|---|---|
| Engineering status | Draft matrix added for review |
| Primary statutory source | Official Bangladesh Laws consolidated Companies Act 1994 and General Clauses Act 1897 |
| Independent counsel approval | **NOT RECORDED** |
| Counsel reviewer / date | Not assigned / not recorded |
| AGM-001 implementation | Deterministic calendar-month calculation; A tests pinned separately |
| AGM-002 interpretation | Open where first-AGM proviso affects later scheduling |
| Court-order effect | Open; no automatic clearance |
| Month-end clamp | Engineering convention; legal confirmation pending |
| Product scoring bands | NLC product policy; not statutory penalty |
| Release authorization | None created by this matrix |

**Do not treat this matrix as a legal opinion, compliance certificate, or approval to release a statutory score.** Any counsel decision must be added with the reviewer, date, source/authority, reasoning, event scope, effective date, and tests demonstrating the resulting behavior.
