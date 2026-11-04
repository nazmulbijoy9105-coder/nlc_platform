# Legal corpus remediation — 4 November 2026

## Release decision

**DO NOT MERGE / DO NOT RELEASE STATUTORY SCORING.**

- 85 canonical IDs exist across the catalogue, seed and approval register.
- VERIFIED_RULE_IDS is empty.
- approved_rule_ids: [] remains unchanged.
- All 85 approval entries remain REVIEW_REQUIRED / score_eligible: false.
- LEGAL_SCORE_RELEASED = False.
- A numeric arithmetic placeholder is not a legal compliance certificate. The risk band remains NOT_EVALUATED.
- Independent Bangladesh-qualified counsel has not signed any rule in this branch.

## Verified code changes in this branch

1. Removed unapproved rules from scoring/BLACK overrides and from BLACK count reporting.
2. Added a release gate that prevents an arithmetic 100 from becoming GREEN.
3. Corrected TAX-002 to surface review prompts from the BDT 30 lakh enlistment threshold; distinguish BDT 30–50 lakh turnover-tax enlistment from VAT registration above BDT 50 lakh. The annual-turnover input is not treated as verified rolling 12-month taxable turnover.
4. TAX-002 remains NOT_EVALUATED pending rolling turnover, mandatory category, taxpayer activity and BIN/registration status verification.
5. VAT-002 is now a review prompt only. Finance Act 2026 (Act 96/2026) changed s.64 from 1 July 2026 to a three-tax-period filing cycle; VAT Amendment Ordinance 2026 (Ordinance 38/2026) replaced s.64 again with effect from 1 October 2026. No automatic late-return finding is emitted without taxpayer class, applicable period, due date, holiday and extension evidence.
6. VAT-003 remains NOT_EVALUATED; no universal annual VAT return duty is assumed without an exact applicable Act/Rule/SRO.
7. TAX-003 now uses the provisional non-individual filing deadline under Income Tax Act 2023 s.170(2), as substituted by Finance Act 2026 (Act 96/2026), with s.171 cross-reference. It is not the former Tax Day formula. Holiday roll-forward, extension and taxpayer-class verification remain open.
8. BSEC-001–004 produce review prompts only, correct the known condition mapping (Condition 1 board composition; Condition 5 audit committee; Condition 9 compliance certificate; Condition 8 website), and do not assume listed-company rules apply to all private companies.
9. LBR-001/002 produce review prompts only unless the applicable section 326 Government direction, establishment class, licence record and renewal terms are verified. The current statute is Bangladesh Labour Act 2006 s.326 as amended by Act 43/2026.
10. Canonical parity audit now recognises tuple-declared BSEC IDs. Canonical integrity tests are being restored rather than silently skipped.

## Statutory anchors identified for counsel confirmation

- Companies Act / RJSC: rule-by-rule source triage identifies material candidate citation defects, including AUD-003 (s.151), CAP-003 (ss.59–60), CHG-001 (s.172), DIR-007 (s.92/Form IX), and STR-001/002/003 (ss.11/12/15–16/20). These are not signed legal conclusions.
- BSEC: Corporate Governance Code 2018, as amended by the 2023 and 2024 notifications; apply only within the instrument's listed-issuer scope.
- VAT: VAT Act 2012 as amended by Act 77/2026 (threshold definitions), Finance Act 2026 Act 96/2026 (multiple VAT provisions, including s.64), and Ordinance 38/2026 (s.64 effective 1 October 2026). NBR Rules, SROs, GOs and taxpayer-specific orders still require exhaustive screening.
- Income tax: Finance Act 2026 Act 96/2026 amended Income Tax Act 2023 s.170 and s.171. Company deadline formula must be verified against s.170(2), not old Tax Day descriptions.
- Labour: Bangladesh Labour (Amendment) Act 2026 Act 43/2026 amended s.326; licensing is direction- and establishment-class-dependent.

## Current blockers

1. Full official Bangla Companies Act amendment history and RJSC form/deadline reconciliation for all company-law rules.
2. All 2026 Income Tax Rules, Withholding Tax Rules, SROs, GOs, circulars and taxpayer-specific extensions screened against TAX-001..004.
3. All 2026 VAT Rules, SROs, GOs, Ordinance 38/2026 text and post-1 October implementation orders screened against TAX-002/VAT-002/VAT-003.
4. Full Labour Rules 2015 amendment history, DIFE directions, factory/establishment classifications, exemptions and licence procedures.
5. All TBD legal provisions resolved with exact official source, commencement, applicability, exceptions and remedy.
6. Independent counsel review and signed disposition for each of 85 rules.
7. Canonical engine/seed/registry/rescue/catalogue/approval/DB/API parity passing with no skipped integrity tests.
8. Full unit and integration suites passing on the latest PR head.

## Required evidence for each rule

Every signed rule record must contain: exact official Act/Gazette/SRO/Rule and section; authentic text extract; publication and commencement dates; retrospective/transitional/repeal effect; duty-holder; company class; trigger; deadline calculation; exceptions/exemptions; extension/condonation/order/stay; required evidence and identity/provenance; legal consequence; separate NLC severity/score rationale; positive and negative test vectors; counsel name, Bangladesh Bar enrolment, signature, date and next review.

## Release criteria

No rule enters approved_rule_ids unless its own complete evidence record is signed by independent Bangladesh-qualified counsel, its negative tests pass, its canonical representations match, and its version is active for the relevant assessment date. Do not enable scoring or BLACK overrides by changing one global flag or by bulk approval.
