# Labour Licensing — Establishment Applicability and Renewal Conflict

**Review date:** 15 November 2026  
**Rules in scope:** LBR-001, LBR-002  
**Release status:** SOURCE REVIEW RECORDED — NOT COUNSEL APPROVED — NOT SCORE ELIGIBLE

> This is a source-mapping and software-control note, not a legal opinion. LBR-001 and LBR-002 remain `REVIEW_REQUIRED`; no score or statutory finding is activated.

## 1. Primary instruments

1. **Bangladesh Labour Act, 2006 (Act No. 42 of 2006)** — section 326.
2. **Bangladesh Labour (Amendment) Act, 2026 (Act No. 43 of 2026)** — section 81 amends section 326(1)(b); the Act states it comes into force immediately.
3. **Bangladesh Labour Rules, 2015 (S.R.O. No. 291-Law/2015)** — rules 354–355, including the registration/licensing process and the legacy licence-validity wording.
4. **Bangladesh Labour (Amendment) Rules, 2026 (S.R.O. No. 53-Law/2026)** — checked as a later rules amendment; the source consulted does not establish a replacement of rules 354–355.

## 2. Correct statutory scope

### Section 326

- Section 326(1)(a) separately controls establishment of a new factory or extension of a factory building without prior approval of the Inspector General. That factory-construction/extension condition must not be conflated with the establishment-licensing condition.
- As amended by Act No. 43 of 2026, section 326(1)(b) empowers the Government to direct **any establishment or factory or any class of factories** to obtain a licence. The amended text provides a five-year renewal period, with a one-year period for contractor agencies.
- The 2026 amendment therefore makes a manufacturing-only applicability predicate unsafe. A commercial establishment, shop, industrial establishment, bank, insurance establishment or contractor establishment may fall within the licensing framework even where the company is not a manufacturing factory.

### Labour Rules 2015, rules 354–355

Rule 354 identifies licensing/registration categories including factories, industrial establishments, commercial establishments, commercial banks, insurance establishments, shops and contractor establishments. The relevant classification is the actual workplace/establishment and activity, not merely the company's legal form or a Boolean `is_manufacturing` field.

Rule 355(2) contains an older validity formulation tied to 30 June of the financial year in which the licence was issued. That wording must be reconciled with the later Act-level five-year renewal term in amended section 326(1)(b), including the treatment of licences issued before the 2026 amendment and the special one-year contractor-agency term. This batch does **not** resolve that interpretive/transitional issue.

## 3. Rule-specific treatment

### LBR-001 — Establishment/factory licence applicability and obtaining

- **Trigger facts:** actual establishment category; whether Rule 354 or an operative Government direction applies; whether a licence was obtained.
- **Not a trigger:** `is_manufacturing=True` alone; a private limited company label alone; or a user-entered `factory_license_obtained=False` without verified DIFE evidence.
- **Applicability evidence:** registered and actual business activity; workplace address; premises and worker facts; classification as factory/industrial/commercial/bank/insurance/shop/contractor establishment; operative Government direction or notification; current rule and Gazette review.
- **Status evidence:** DIFE registry search with date and search scope, inspection record or authenticated licence copy, application/Form 77 and receipt, issue date and licence holder details.
- **Evaluator behaviour:** if scope review is absent, emit UNKNOWN/NOT_EVALUATED; if scope is verified as non-applicable, do not trigger; if scope applies but licence status is unverified, emit UNKNOWN; if a verified search establishes no licence, preserve a lawyer-review candidate, never a score-bearing breach before counsel approval.

### LBR-002 — Licence expiry/renewal

- **Trigger facts:** a verified applicable licensing duty, verified licence status, and the expiry date printed on the issued licence.
- **Do not calculate:** do not infer an expiry date by adding one or five years to the issue date until counsel resolves amended section 326(1)(b), Rule 355(2), contractor classification and transitional treatment.
- **Evidence:** complete licence copy including printed expiry; renewal application and receipt; DIFE decision; establishment/contractor classification; current Gazette and rule amendments.
- **Evaluator behaviour:** missing printed expiry is UNKNOWN. A printed expiry in the past is a lawyer-review candidate with zero score impact, not an automatic statutory breach.

## 4. Implementation changes

The evaluator no longer uses manufacturing status as the LBR-001/LBR-002 licensing gate. It requires explicit scope-review metadata:
- `labour_establishment_category`
- `labour_license_scope_verified`
- `labour_license_scope_evidence_ref`
- `labour_license_scope_verified_at`
- `labour_license_scope_verified_by`

It separately requires verified licence-status metadata:
- `labour_license_status_verified`
- `labour_license_status_evidence_ref`
- `labour_license_status_verified_at`
- `labour_license_status_verified_by`

The legacy field `factory_license_required_by_direction` is retained for compatibility but now represents the reviewed s. 326/r. 354 licensing requirement for the establishment category. The actual licence expiry date is used only when present on the verified licence copy.

All candidate outputs remain NOT_EVALUATED with zero score impact pending independent rule approval.

## 5. Sources checked

1. **Official Bangladesh Laws — Bangladesh Labour (Amendment) Act, 2026 (Act No. 43 of 2026), s. 81:** https://bdlaws.minlaw.gov.bd/act-print-1672.html
2. **Official Gazette — Bangladesh Labour (Amendment) Act, 2026:** https://dpp.gov.bd/upload_file/gazettes/14212_75510.pdf
3. **Official Gazette — Bangladesh Labour Rules, 2015 (S.R.O. No. 291-Law/2015):** https://dpp.gov.bd/bgpress/bangla/index.php/home/download_file/gazettes/3910_55154.pdf
4. **Official Gazette — Bangladesh Labour (Amendment) Rules, 2026 (S.R.O. No. 53-Law/2026):** https://dpp.gov.bd/bgpress/bangla/index.php/home/download_file/gazettes/59944_60708.pdf
5. **Working English transcription of Rule 354 and the 2026 amendment (secondary cross-check):** https://bdadvocacy.com/bangladesh-labour-act-amendment-2026/

**Source limitation:** the Bengali Act and Gazette text control. The exact operative Government direction(s), current DIFE category practice, the continuing force of Rule 354 after the 2026 Act, and the Rule 355(2) renewal-term conflict require a named Bangladesh labour-law counsel opinion before LBR-001 or LBR-002 can be approved.
