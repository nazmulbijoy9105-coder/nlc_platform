# 59-rule register vs 85-rule repository catalogue — discrepancy report

**Observation date:** 2026-11-28  
**Repository ref:** `main`  
**Seed file:** `scripts/seed_rules.py`  
**Seed blob SHA:** `943771bec6adb94ca0231791e7393ab24a679b78`  
**Purpose:** compare the 59-row legal authority workpaper with the current 85-rule seed and 85-row RJSC scope decision register. This is a reconciliation workpaper, not legal approval.

## 1. Inventory and identity parity

- Repository seed definitions parsed: **85**.
- Scope decision register rows: **85**.
- Scope IDs vs seed IDs: exact **85/85** parity; no duplicates or missing IDs.
- Legal authority register rows: **59**.
- Legal authority register IDs matched to seed IDs: **59/59**.
- Scope decisions: **59 IN_SCOPE_RJSC**, **26 OUT_OF_SCOPE**.
- All 59 legal-register IDs are marked IN_SCOPE_RJSC in the scope register; none of the 26 OUT_OF_SCOPE IDs appear in the 59-row legal register.
- Scope counsel decisions and counsel names recorded: **0**. These are project working classifications, not counsel-approved legal determinations.

## 2. Field-level differences

Compared as literal values, not as conclusions on legal correctness:

- Statutory-basis string differences: **29**.
- Rule-name differences: **17**.
- Missing register IDs: **0**.
- Missing seed IDs from the 85-row scope register: **0**.

### 2.1 Statutory-basis differences

| Rule ID | 59-register recorded basis | Current repository seed basis |
|---|---|---|
| AGM-001 | Section 81, Companies Act 1994 (Bangladesh) | Section 81(1), Companies Act 1994 (Bangladesh) |
| AGM-002 | Section 81, Companies Act 1994 (Bangladesh) | Section 81(1), Companies Act 1994 (Bangladesh) |
| AGM-003 | Section 85, Companies Act 1994 (Bangladesh) | Section 85(1)(a), Companies Act 1994 (Bangladesh) |
| AGM-004 | Section 85, Companies Act 1994 (Bangladesh) | Section 85(1)(a), Companies Act 1994 (Bangladesh) |
| AGM-005 | Section 89, Companies Act 1994 (Bangladesh) | Section 85(2)(b), Companies Act 1994 (Bangladesh), read with the Articles |
| AGM-007 | Section 130, Companies Act 1994 (Bangladesh) | Companies Act 1994, Section 85 and the company Articles; exact adjournment provision requires counsel verification |
| AR-002 | Section 36 and Schedule X (annual-return duty); Section 346 is a separate Registrar strike-off process | Section 36 and Schedule X (annual-return duty); Section 346 governs a separate Registrar strike-off procedure. |
| AR-003 | Section 36 and Schedule X (annual-return duty); Section 346 requires separate Registrar grounds and notice steps | Section 36 and Schedule X (annual-return duty); Section 346 requires separate Registrar grounds and statutory notice steps. |
| AUD-003 | Sections 151, 210, Companies Act 1994 (Bangladesh) | Sections 183 and 210, Companies Act 1994 (Bangladesh) |
| AUD-004 | Section 210(2), Companies Act 1994 (Bangladesh) | Section 210(3), Companies Act 1994 (Bangladesh) |
| CAP-004 | Section 88, Companies Act 1994 (Bangladesh) | Section 88(1), Companies Act 1994 (Bangladesh) — 15 days |
| DEF-001 | Section 94, Companies Act 1994 (Bangladesh) | Section 94(1)(d), Companies Act 1994 (Bangladesh) |
| DEF-002 | Section 397, Companies Act 1994 (Bangladesh) | Case-specific enabling provision required; not a universal section |
| DIR-001 | Section 90, Companies Act 1994 (Bangladesh) | Section 115(2), Companies Act 1994 (Bangladesh) |
| DIR-002 | Section 93, Companies Act 1994 (Bangladesh) | Section 115(2), Companies Act 1994 (Bangladesh) |
| DIR-004 | Section 109, Companies Act 1994 (Bangladesh) | Section 115, Companies Act 1994 (Bangladesh) |
| DIR-005 | Section 130, Companies Act 1994 (Bangladesh) | Companies Act 1994, Section 130 (director-interest disclosure); generic register duty/title requires legal reconciliation |
| DIR-006 | Section 130, Companies Act 1994 (Bangladesh) | Companies Act 1994 and applicable Articles; exact register obligation requires counsel verification |
| DIR-008 | Sections 195 and 197; section 199 where related entities are included, Companies Act 1994 (Bangladesh) | Section 104, Companies Act 1994 (Bangladesh) |
| INC-003 | Section 90(2), Companies Act 1994 (Bangladesh) | Sections 90(1) and 90(2), Companies Act 1994 (Bangladesh) |
| INC-004 | Section 53, Companies Act 1994 (Bangladesh) | Section 56, Companies Act 1994 (Bangladesh) — applicability and consequences require lawyer review |
| REG-001 | Section 34, Companies Act 1994 (Bangladesh) | Companies Act 1994 (Bangladesh) and applicable Articles; individual register duties require their own statutory mapping |
| REG-002 | Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh) | Sections 34, 89, 174, Companies Act 1994 (Bangladesh) |
| REG-003 | Section 34(2), Companies Act 1994 (Bangladesh) | Unresolved location proposition; Companies Act 1994 (Bangladesh) |
| STR-001 | Section 20, Companies Act 1994 (Bangladesh) | Sections 11 and 88(1), Companies Act 1994 (Bangladesh) |
| STR-002 | Section 17, Companies Act 1994 (Bangladesh) | Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh) |
| STR-003 | Section 18, Companies Act 1994 (Bangladesh) | Sections 20 and 88(1), Companies Act 1994 (Bangladesh) |
| TR-003 | Section 38(7), Companies Act 1994 (Bangladesh), and the company's Articles | Section 38(7), Companies Act 1994 (Bangladesh), and the company’s Articles |
| TR-005 | Section 38(7), Companies Act 1994 (Bangladesh), and the company's Articles | Section 38(7), Companies Act 1994 (Bangladesh), and the company’s Articles |

### 2.2 Rule-name differences

| Rule ID | 59-register name | Current repository seed name |
|---|---|---|
| AGM-003 | AGM Notice Defective — Insufficient Days | AGM Short Notice — Consent Verification |
| AGM-004 | AGM Notice Missing | AGM Notice or Short-Notice Consent Missing |
| AGM-006 | AGM Minutes Not Prepared | AGM Minutes Status Requires Verification |
| AGM-007 | AGM Adjourned Without Proper Notice | AGM Adjournment Notice Requires Review |
| AUD-003 | AGM Held Without Completed Audit — BLACK OVERRIDE | AGM Held Without Completed Audit |
| AUD-005 | Subsequent Auditor Not Appointed | Subsequent Auditor Reappointment Status Unknown |
| BOD-001 | Board Meeting Not Held Within Quarter | Board Meeting History Requires Verification |
| BOD-002 | Board Meeting Notice Not Given | Board Meeting Notice Status Requires Verification |
| BOD-003 | Board Meeting Minutes Not Prepared | Board Minutes Status Requires Verification |
| DIR-004 | Departed Director Still Active on RJSC Register | Late Director Cessation Filing - Legal Effect Review |
| DIR-005 | Register of Directors Interests Missing | Director Interest Disclosure/Register Requires Review |
| DIR-006 | Register of Contracts Missing | Register of Contracts Requires Review |
| DIR-008 | Director Holding Office of Profit Without Consent | Office of Profit Status Requires Verification |
| DIR-010 | Managing Director Appointed for More Than 5 Years | Managing Director Term Requires Verification |
| INC-004 | Paid-Up Capital Exceeds Authorized Capital | Paid-Up / Authorized Capital Mismatch — Legal Review |
| SH-002 | Share Certificates Not Issued Within 60 Days | Share Certificates Not Issued Within 90 Days |
| TR-001 | Share Transfer Instrument — Section 38(3) Evidence Review | No Share Transfer Instrument — Form 117 |

A string difference does not automatically mean the repository or register is legally wrong. Each difference must be resolved by exact statutory text, the actual rule condition, and the relevant evidence event. Keep original recorded values traceable; do not silently overwrite them.

## 3. Source-supported findings and corrections (not approvals)

1. **AGM-001 / AGM-002:** the current Companies Act text identifies section 81(1), not a bare unqualified “section 81” reference. The first-AGM 18-month proviso and subsequent annual/15-month rules are distinct. The precise month-end calculation and the interaction of provisos still require legal interpretation review. Official text: https://bdlaws.minlaw.gov.bd/act-print-788.html.
2. **AGM-003 / AGM-004:** section 85(1)(a) is the notice provision; the current consolidated text shows 21 days. The Companies (Second Amendment) Act 2020 changed the period from 14 to 21 days. Short-notice consent and the legal consequence of non-service remain review points. Official Gazette: https://www.dpp.gov.bd/upload_file/gazettes/37932_40268.pdf.
3. **AGM-005 / AGM-006:** section 89 concerns minutes, not quorum. Quorum is addressed in section 85(2)(b), subject to the company's Articles. Section 89 remains relevant to minutes. Official text: https://bdlaws.minlaw.gov.bd/act-print-788.html.
4. **AGM-007:** the register's section 130 citation is not substantiated as an adjourned-meeting notice provision. The repository's section 85 / Articles candidate is plausible, but exact subsection and application remain unresolved.
5. **AR-002 / AR-003:** section 36 and Schedule X are the annual-return basis. Section 346 is a separate Registrar strike-off process; it must not be treated as the annual-return duty.
6. **AUD-003:** section 151 concerns return of allotment; section 183 concerns accounts laid before the AGM; section 210 concerns auditors. The register's combined section 151/210 basis does not support an “AGM held without completed audit” rule as framed. The repository's sections 183/210 mapping is better aligned to the stated rule, subject to counsel review of trigger/evidence and any exceptions.
7. **AUD-004:** the repository points to section 210(3), while the register says 210(2). Verify the precise appointment/reappointment subsection against the official text before approval.
8. **DIR-001 / DIR-002 / DIR-004:** section 90 is minimum director numbers; section 93(2) concerns written consent to act and a 30-day filing; section 115(2) concerns director particulars and changes within 14 days. These are separate duties and must not be collapsed into one deadline.
9. **DIR-008:** sections 195/197/199 concern investigation matters; section 104 is the office-of-profit provision. The repository mapping is materially closer to the stated rule title, but exceptions and the consent mechanism require legal review.
10. **DEF-002:** section 397 should not be used as a universal penalty provision for every statutory return or filing. A case-specific enabling provision is required.
11. **SH-002:** section 158(1) specifies 90 days, including after registration of transfer, not 60 days. The 59-register title is stale; the repository title states 90 days. Event coverage for transfer registration must still be checked.
12. **TR-001:** the 2020 Second Amendment inserted section 38(3A) concerning transferor-signature verification. The repository title “No Share Transfer Instrument — Form 117” and register title “Section 38(3) Evidence Review” are not the same rule proposition; reconcile the exact duty and evidence condition.
13. **TR-002:** the official Finance Act 2022 Gazette substitutes Schedule I to the Stamp Act. The share-transfer entry is **Article 61(a)**, at 1.5% of consideration, with a separate listed-public-company exemption. **Article 62 is transfer of lease.** This corrects the earlier Article 62(a) note in the working register. See the derived excerpt and capture log. Later amendments, including the listed SRO No.386-Law/2026, remain unreviewed.
14. **REG-001 / REG-002 / REG-003:** the register combines distinct register-keeping and location propositions. Section 34(2) cannot be treated as a universal registered-office location rule without exact subsection text and register-specific analysis. Split composite duties; keep unresolved items in review.
15. **INC-004:** the register cites section 53; the repository cites section 56. The precise capital condition and the effect of an excess over authorised capital need provision-specific review; no automatic invalidity conclusion should be inferred.

## 4. Unresolved work

- 29 literal statutory-basis differences and 17 rule-name differences are recorded above; not every one is resolved by the source observations.
- No exhaustive amendment/repeal chronology has been established for all 59 entries.
- No commencement notice or source file has been hashed in this execution.
- No independent reviewer or counsel disposition has been entered.
- No rule is promoted to verified or approved by this report.
- Do not change `VERIFIED_RULE_IDS`, scoring eligibility, risk bands, score hashes, rescue triggers, or release gates as a result of this reconciliation.

## 5. Required handling

For each remaining difference: preserve the original register value; cite the exact current and historical instrument; record the operative period; state the actual evidence/event condition; record the repository mapping; and leave the disposition `NOT_VERIFIED` until independent legal review and explicit counsel disposition are completed.
