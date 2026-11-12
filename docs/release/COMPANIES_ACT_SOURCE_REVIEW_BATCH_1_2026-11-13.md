# Companies Act 1994 — source review batch 1 (13 November 2026)

## Scope and decision boundary

This is a source-review workpaper for the first high-impact Companies Act rules. It is not a Bangladesh legal opinion, does not amend the rule seed, does not change evaluator behavior, and does not authorize production writes. A citation being found is not the same as validating the complete legal proposition, applicability, amendment history, remedy, or effective date.

Primary-source hierarchy for final approval:
1. Promulgated Bangladesh Gazette / official consolidated Laws of Bangladesh text.
2. RJSC official guidance for filing process and forms (administrative guidance; not a substitute for the Act).
3. Professional commentary/manuals only as corroboration, never as sole authority for a statutory proposition.

## Findings

| Rule / issue | Source evidence found | Technical/legal disposition | What remains before rule change |
|---|---|---|---|
| AGM-001 / AGM-002 — AGM timing | Official Laws of Bangladesh Act page identifies s.81 and related penalty provision s.82. The English statutory text reproduced by ICSI and ICNL states: AGM in each Gregorian calendar year; no more than 15 months between AGMs; first AGM within 18 months of incorporation; if first AGM held in that period, no AGM required in incorporation year or following year; Registrar may extend a later AGM (not first AGM) on application within 30 days after expiry, up to 90 days or 31 December, whichever earlier. | The seed's 18-calendar-month first-AGM rule and 15-month subsequent interval are directionally supported. The database's fixed 548/456/182-day thresholds are not equivalent to calendar-month/calendar-year statutory logic and must not be accepted as a substitute. The seed description also needs explicit treatment of the Registrar-extension proviso and calendar-year duty. | Confirm authoritative English/Bengali consolidated text and amendment chain; implement calendar arithmetic, calendar-year condition, extension evidence and first-AGM exception; build boundary-date tests. No fixed-day approximation. |
| AGM-003 / AGM-004 — notice and short notice | Official Laws of Bangladesh s.85 page confirms at least 21 days' written notice. The accessible full s.85 text states shorter AGM notice is permitted with written consent of all members entitled to attend and vote. It also states accidental omission to give notice or non-receipt by a member does not invalidate proceedings. | A blanket rule that treats every notice interval below 21 days as FAIL is legally incomplete. The seed's short-notice consent gate is closer to the statutory structure, but its evaluator must distinguish verified consent, verified absence of consent, and unknown evidence. The accidental omission/non-receipt exception must be represented. | Verify exact service/clear-day counting method from the controlling text and applicable Articles; add consent and omission/non-receipt evidence; keep UNKNOWN when evidence is incomplete. Do not assert invalidity of all resolutions. |
| AGM-005 — quorum | The full s.85(2)(b) text states, subject to contrary provision in the Articles: private company with no more than six members — two members; private company with more than six — three; other companies — five members personally present. | The seed's statutory default description matches the member-count tiers, but its condition is not sufficient unless quorum_required is derived from verified Articles and member count. The DB description's evidence gates are safer; ensure evaluator really enforces them. | Verify current Articles, member register and attendance; make Articles override statutory default; test 6 vs 7 members and UNKNOWN facts. |
| AGM-006 — minutes | Official Laws of Bangladesh s.89 requires minutes of general meetings and directors' meetings to be entered in books kept for that purpose; signed minutes have evidentiary effect and create rebuttable presumptions. | Seed citation to s.89 is supported. The seed's review-prompt wording is safer than a definitive claim that minutes were not prepared based solely on a missing user-entered flag. | Require minute-book evidence and verification status; do not treat absence of upload as proof of non-existence. |
| OFF-001 — registered office | Official Laws of Bangladesh places the registered-office duty in s.77, including notice of registered-office location/change to Registrar within 28 days. | Any OFF-001 citation to s.81 is incorrect for the registered-office duty. | Confirm exact OFF-001 proposition and separate registered-office existence from notice-of-situation/change filing. Preserve separate identities if the rule combines distinct duties. |
| DIR-001 / DIR-002 — Form XII | RJSC official FAQ identifies Form XII particulars and changes, filed within 14 days of appointment or change, citing s.115. | Section 115 is supported for Form XII filing by the regulator's guidance. A seed citation to s.92 for Form XII is not supported by this guidance; s.92 relates to director consent/appointment matters. | Verify exact text of s.115 and distinguish filing particulars from the legal validity/effective date of appointment, resignation, removal or death. |
| SH-001 — return of allotment | RJSC official FAQ says Form XV is filed within 60 days of allotment under s.151. The reproduced text of s.151(1) requires a return within 60 days and s.151(3) allows Registrar extension on application before expiry. | The 60-day deadline is corroborated. The evaluator must account for extension evidence and the actual allotment event, not merely an arbitrary last-allotment date. | Confirm current prescribed forms and exact statutory documents against official consolidated text; add extension handling and event-level evidence. |
| AUD-001 — first auditor | ICAB's 2021 Corporate Laws Manual reproduces s.210(6): first auditor appointed by Board within one month from registration, holding office until conclusion of first AGM. | This supports the seed's one-calendar-month concept as corroboration, but the source located in this pass is a professional manual, not the official consolidated Act text. Do not mark fully source-validated yet. | Obtain controlling official Act text and amendment chain; retain calendar-month calculation; model general-meeting appointment fallback where Board fails, after counsel review. |

## Primary / corroborating sources

- Laws of Bangladesh, Companies Act 1994, official consolidated Act page: https://bdlaws.minlaw.gov.bd/act-print-788.html
- Laws of Bangladesh, s.85 (official section page): https://bdlaws.minlaw.gov.bd/act-print-788/section-print-32909.html
- Laws of Bangladesh, s.77 / s.89 extract (official Act-part page): https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html
- RJSC official FAQs (Forms IV, XII, XV and filing periods): https://ebrs.roc.gov.bd/public/faqs
- ICSI-hosted English text of the Companies (Bangladesh) Act 1994 (corroborating copy; not treated as official promulgation): https://www.icsi.edu/Portals/86/Bare%20ACTS/Bangladesh%20COMPANIES%20ACT.pdf
- ICAB Corporate Laws and Practices manual (2021; corroboration for s.210(6), not primary law): https://www.icab.org.bd/icabadmin/uploads/ckeditor/6665Corporate%20Laws%20Manual%20Final%202021.pdf

## Required engineering controls before any release

1. Do not copy all seed values into production or vice versa.
2. Keep PENDING, NOT_EVALUATED, score impact zero, and BLACK override false until rule-level legal approval and evidence contracts are complete.
3. Add date-boundary vectors for first AGM (18 calendar months), later AGM (calendar year and 15 calendar months), Registrar extension (30-day application window; max 90 days / 31 December), and month-end/leap-year behavior.
4. Add notice vectors for 21-day notice, valid written short-notice consent by all eligible members, verified absence of consent, accidental omission/non-receipt, and unknown evidence.
5. Add quorum vectors for private companies with 6 and 7 members, Articles overriding the default, and incomplete Articles/member/attendance evidence.
6. Add provenance fields for source URL, exact provision/subsection, source language, amendment/effective interval, retrieval date, reviewer, and counsel approval record.
7. Have Bangladesh-qualified company-law counsel approve each final proposition and product owner approve evaluator semantics before forward-only migration or production scoring.

## Status

This batch establishes source-backed findings and open conditions. It does not close any legal-approval gate and does not change seed, database, migrations, production scores, deadlines, or calendar events.
