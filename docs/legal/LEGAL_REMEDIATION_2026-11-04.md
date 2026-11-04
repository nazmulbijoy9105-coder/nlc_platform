# Legal corpus remediation — 2026-11-04

## Release decision

**Legal scoring is fail-closed.** The 85 active seed rule IDs are all marked
`REVIEW_REQUIRED` in `legal_approval_register.yaml`. No rule is currently
approved for production scoring. This is intentional: internal code review,
a passing test, a section-number lookup, or an RJSC form catalogue is not
independent legal sign-off. Provisional findings may be displayed for review,
but they must not reduce the statutory compliance score or force a BLACK
override until approved.

## Changes made in this branch

1. `VERIFIED_RULE_IDS` is empty until a signed legal approval register exists.
2. BLACK overrides are now subject to the same approval gate as score deductions.
3. Corrected the RJSC form reference catalogue:
   - Form IX: director consent, s.92, 30 days.
   - Form XII: particulars of directors/managers and changes, s.115, 14 days.
   - Schedule X: annual return, s.36, 21 days after AGM (not Form XII).
   - Form XV: return of allotment, s.151, 60 days.
   - Form IV: increase of share capital, s.56, 15 days.
   - Form XVIII: creation of charge, s.159, 21 days.
   - Form XIX: modification of charge, s.167(3), 21 days.
   - Form XXVIII: satisfaction of charge, s.172, 21 days per RJSC process FAQ.
   - Form 23B: auditor's notice of appointment, s.210(2), 30 days.
4. Corrected engine and seed anchors for:
   - Name change: s.11; resolution copy filing s.88(1), 15 days.
   - Memorandum alteration: s.12 and, where applicable, court confirmation/registration under ss.15–16; resolution copy filing s.88(1), 15 days.
   - Articles alteration: s.20; resolution copy filing s.88(1), 15 days.
   - Capital reduction: ss.59–60, not s.150.
   - Charge satisfaction: s.172/Form XXVIII, not s.159/Form XIX.
   - Special resolution copy filing: s.88(1), 15 days.
   - Income-tax advance instalments: s.155(2), 15 September, 15 December, 15 March and 15 June; s.155(3) moves a public-holiday date to the next working day.
   - VAT registration and turnover-tax enlistment are distinct: NBR FAQ states registration above BDT 8m and enlistment above BDT 3m in a 12-month period, application within 15 days. Existing TAX-002 now tests the BDT 8m registration threshold only; the turnover-tax enlistment obligation needs its own rule and data model.
   - Labour licensing: s.326 of the Labour Act, as amended in 2026, not s.35; licensing is conditional on Government directions / establishment class. Five-year licence renewal and one-year contractor-agency licence need class-aware handling.
   - BSEC references identify the 2018 Corporate Governance Code as amended in 2023 and 2024; Condition 1 is board composition and Condition 5 is audit committee. Listed-company applicability and each amendment's effective date still need rule-level logic.

## Rule inventory discrepancy

The current `scripts/seed_rules.py` contains **85 unique active rule IDs** (90 textual occurrences including duplicates). Earlier audit notes expected 86 active engine rules. This is an unresolved one-rule inventory/parity discrepancy. Do not silently invent or reactivate a ghost rule to make the count match. Reconcile engine, seed, DB rows, migrations and API output by exact rule ID before claiming parity.

## Rule-by-rule legal review still required

All 85 IDs in `legal_approval_register.yaml` remain unapproved. Review each against the
law and subordinate instruments effective on the assessment date. At minimum:

- **Companies Act / RJSC:** INC, AGM, AUD, AR, DIR, REG, OFF, SH, TR, CAP, CHG, STR,
  ACC, BOD, MEM, DEF, ESC. Confirm the exact duty-holder, trigger date, calendar-day
  versus working-day convention, company class, Articles, statutory exceptions,
  Registrar extensions, court orders, penalty and consequence. Split combined rules
  where one rule currently conflates different legal duties.
- **Income tax:** TAX-001..004. The engine's current company return deadline formula
  and extension boolean are not approved. Implement the current Tax Day definition,
  assessment-year amendments, special company Tax Day alternatives, holiday rule,
  taxpayer exclusions and only a verified extension order/date. Advance tax must
  account for s.155(3) holidays, s.156 new assessee treatment and actual payment/
  adjustment records.
- **VAT:** TAX-002 / VAT-002 / VAT-003. Add a separate turnover-tax enlistment rule,
  period-specific monthly/quarterly returns, correct VAT forms and effective-dated
  threshold schedules. NBR FAQ alone is not a substitute for the operative Act,
  Rules, SROs and Finance Act for the relevant period.
- **Labour:** LBR-001..003. Apply the Labour Act amendment dated 16 April 2026,
  Labour Rules and DIFE directions. Resolve establishment type, worker count,
  factory/establishment class, licence direction, renewal period, contractor status,
  and order-specific scope.
- **BSEC:** BSEC-001..004. Version the 2018 Code and 2023/2024 amendments; do not
  apply listed-company obligations to ordinary private companies. Test all conditions,
  not a single boolean for independent director/audit committee.
- **Foreign investment / FX:** INC-005, INC-006, FX-001. Replace generic USD thresholds
  and blanket violation flags with specific dated BIDA/BB circulars, AD-bank evidence,
  remittance category, investor type, work-permit rule and transaction facts.
- **Local licences:** TL-001..002. Resolve the relevant City Corporation / Paurashava /
  local authority law, trade category, location, renewal cycle and exemptions.
- **Insolvency / winding-up:** BNK-001..003 and ESC-004..005. Distinguish Companies Act
  winding-up proceedings, Bankruptcy Act proceedings, liquidation status, petition,
  order, appointment, investigation and procedural stage. Do not use generic
  Bankruptcy Act section numbers for Companies Act winding-up.
- **Penalty notices:** DEF-002. A notice cannot be mapped to one universal penalty
  provision; store the notice, alleged offence, enabling section, authority, response
  deadline, appeal/stay and disposition.
- **Transfer / registers / accounts:** TR-001..006, REG-001..003, ACC-001..003,
  SH-001..003, DIR-005..006. Split each distinct register, transfer, filing, accounts
  presentation and certificate obligation into its own evidence-backed test.

## Primary sources checked for this remediation

- Bangladesh Companies Act 1994, official consolidated text:
  https://bdlaws.minlaw.gov.bd/act-print-788.html
- RJSC eBRS filing FAQ (forms and filing periods):
  https://ebrs.roc.gov.bd/public/faqs
- ICAB Corporate Laws & Practices (2024), statutory filing periods:
  https://www.icab.org.bd/icabadmin/uploads/ckeditor/1384Corporate%20Laws%20%26%20Practices.pdf
- NBR authentic English Income Tax Act 2023 / amendments listing:
  https://nbr.gov.bd/regulations/acts/income-tax-acts/eng
- NBR authentic Income Tax Act 2023 PDF (s.155 advance tax dates):
  https://nbr.gov.bd/uploads/acts/Income_tax_act_2023.pdf
- NBR VAT FAQ (registration/enlistment thresholds and 15-day application):
  https://nbr.gov.bd/faq/vat-faq/eng
- Bangladesh Labour Act, official BDLaws:
  https://bdlaws.minlaw.gov.bd/act-details-952.html?lang=en
- Ministry of Labour legislative information (Bangladesh Labour Amendment Act 2026):
  https://mole.gov.bd/pages/legislative-informations

## Important limitations

This branch does not claim that all 85 rules are legally validated. It prevents
unapproved rules from producing a statutory score while the missing rule-by-rule
legal work is completed. The rule catalogue, migration seed history, existing
database rows, filing APIs, frontend labels and PDF reports must still be reconciled
against this register. A Bangladesh-qualified independent reviewer must approve
each rule and its applicable law version before any ID is added to the allowlist.
