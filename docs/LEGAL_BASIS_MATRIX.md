# ILRMF Legal Basis Matrix

**STATUS: INTERNAL ENGINE INVENTORY ONLY — NOT PRIMARY-SOURCE LAWYER-VALIDATED OR COUNSEL-APPROVED**  
**PENDING:** Independent Bangladesh legal review before commercial legal sign-off  
**REVIEWER:** [TO BE ASSIGNED]  
**TARGET DATE:** [TO BE SET]  

Version: **2.2.0**  
Date: 2026-11-02  
Branch: main @ production-gate  
Rule corpus: **85** ILRMF rules (engine ↔ seed ID + statutory_basis parity)

This matrix is a technical inventory of candidate legal anchors and internal rule-policy defaults. It is not a legal opinion, statutory compliance certificate, or counsel approval register. Engine/seed parity proves only that two code representations agree; it does not prove that either representation states current law correctly.

 > **Release and legal-status note (2026-11-06):** `LEGAL_SCORE_RELEASED = False`. All 85 rules remain subject to individual independent Bangladesh-qualified counsel review. The internal source-check allowlist is not legal approval. Severity, deduction, BLACK override and deadline defaults are product-policy proposals, not statutory consequences. Unknown applicability, incomplete evidence, missing current source or unresolved amendment chronology must remain `NOT_EVALUATED`.

| Rule ID | Rule Name | Statutory Basis (engine) | Severity | Score | Black | Status |
|---------|-----------|--------------------------|----------|-------|-------|--------|
| ACC-001 | Financial Statements Not Presented at AGM | Section 183, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| ACC-002 | Financial Statements Not Filed with Registrar | Section 190, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| ACC-003 | Books of Account Not Kept | Section 181, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| AGM-001 | First AGM Default | Section 81, Companies Act 1994 (Bangladesh) | RED | 20 | no | Engine-aligned 2026-11-02 |
| AGM-002 | Subsequent AGM Default | Section 81, Companies Act 1994 (Bangladesh) | RED | 20 | no | Engine-aligned 2026-11-02 |
| AGM-003 | AGM Notice Defective — Insufficient Days | Section 85, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| AGM-004 | AGM Notice Missing | Section 85, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| AGM-005 | AGM Quorum Not Met | Section 85(2)(b), Companies Act 1994 (Bangladesh), subject to the company’s Articles | RED | 15 | no | INTERNAL TRIAGE — verify Articles, member count and attendance evidence |
| AGM-006 | AGM Minutes Not Prepared | Section 89, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| AGM-007 | AGM Adjourned Without Proper Notice | Section 85 and applicable Articles; exact adjournment provision requires counsel mapping | NOT_EVALUATED | 0 | no | REVIEW ONLY — no automatic default |
| AR-001 | Annual Return Default — Single Year | Section 36 (Schedule X), Companies Act 1994 (Bangladesh) | YELLOW | 10 | no | Engine-aligned 2026-11-02 |
| AR-002 | Annual Return 2-Year Backlog | Sections 36 and 304, Companies Act 1994 (Bangladesh) | RED | 20 | no | Engine-aligned 2026-11-02 |
| AR-003 | Annual Return 3-Year Backlog — Strike-Off Risk | Sections 36 and 304, Companies Act 1994 (Bangladesh) | BLACK | 20 | no | Engine-aligned 2026-11-02 |
| AR-004 | Annual Return Filed But Incomplete | Section 36, Schedule X, Companies Act 1994 (Bangladesh) | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| AUD-001 | First Auditor Not Appointed Within One Calendar Month | Section 210(6), Companies Act 1994 (Bangladesh) | YELLOW | 10 | no | Engine-aligned 2026-11-02 |
| AUD-002 | Audit Not Completed Before AGM | Section 183, Companies Act 1994 (Bangladesh) | RED | 12 | no | Engine-aligned 2026-11-02 |
| AUD-003 | AGM Audit Status Requires Legal Review | Section 183, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Audit/account evidence and legal consequences require case-specific review; no automatic BLACK override |
| AUD-004 | Auditor Reappointment Requires Legal Review | Section 210(3), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Verify statutory exceptions and notice requirements before determining non-compliance |
| AUD-005 | Subsequent Auditor Reappointment Status Unknown | Section 210(3), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Evidence-status only; no 120-day deadline; exceptions require legal review |
| BNK-001 | Winding Up Petition Filed | Bankruptcy Act 1997 (Bangladesh), Section 12 | BLACK | 10 | YES | Engine-aligned 2026-11-02 |
| BNK-002 | Liquidator Appointed | Bankruptcy Act 1997 (Bangladesh), Section 14 | BLACK | 10 | YES | Engine-aligned 2026-11-02 |
| BNK-003 | Court-Ordered Winding Up | Bankruptcy Act 1997 (Bangladesh), Section 18 | BLACK | 35 | YES | Engine-aligned 2026-11-02 |
| BOD-001 | Board Meeting Not Held Within Quarter | Section 96, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| BOD-002 | Board Meeting Notice Not Given | Section 95, Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| BOD-003 | Board Meeting Minutes Not Prepared | Section 89, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| BSEC-001 | BSEC Quarterly Report Not Filed | Applicable BSEC listing/securities reporting instrument; exact rule, issuer class, period and due date unresolved (not CG Code Condition 8) | NOT_EVALUATED | 0 | no | REVIEW ONLY — listed issuer scope and instrument required |
| BSEC-002 | CG Certificate Not Obtained | BSEC Corporate Governance Code 2018, Condition 9, as amended; listed-issuer scope only | NOT_EVALUATED | 0 | no | REVIEW ONLY — certifier, AGM appointment and evidence required |
| BSEC-003 | Board Composition Non-Compliant | BSEC Corporate Governance Code 2018, Condition 1, as amended; listed-issuer scope only | NOT_EVALUATED | 0 | no | REVIEW ONLY — current amendment and director eligibility required |
| BSEC-004 | Audit Committee Not Established | BSEC Corporate Governance Code 2018, Condition 5, as amended; listed-issuer scope only | NOT_EVALUATED | 0 | no | REVIEW ONLY — committee composition and duties required |
| CAP-001 | Capital Alteration Without Proper Resolution | Section 53, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| CAP-002 | Charge Not Registered With RJSC Within 21 Days | Section 159(1), Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| CAP-003 | Capital Reduction Without Court Order | Sections 59-60, Companies Act 1994 (Bangladesh) | BLACK | 15 | YES | Engine-aligned 2026-11-02 |
| CAP-004 | Special Resolution Not Filed With RJSC within 15 days | Section 88(1), Companies Act 1994 (Bangladesh) | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| CHG-001 | Charge Satisfaction Not Filed | Section 172, Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| DEF-001 | Director Disqualified | Section 94, Companies Act 1994 (Bangladesh) | BLACK | 20 | YES | Engine-aligned 2026-11-02 |
| DEF-002 | Unresolved Penalty Notices | Case-specific enabling provision; no universal section | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| DIR-001 | Director Appointment Particulars Not Filed Within 14 Days | Section 115, Companies Act 1994 (Bangladesh) | YELLOW | 10 | no | Engine-aligned 2026-11-02 |
| DIR-002 | Director Cessation Particulars Not Filed Within 14 Days | Section 115, Companies Act 1994 (Bangladesh) | YELLOW | 10 | no | Engine-aligned 2026-11-02 |
| DIR-003 | Major Director Filing Irregularity — Over 1 Year | Section 115, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| DIR-004 | Departed Director Still Active on RJSC Register | Section 109, Companies Act 1994 (Bangladesh) | RED | 10 | no | Engine-aligned 2026-11-02 |
| DIR-005 | Register of Directors Interests Missing | Section 130, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| DIR-006 | Register of Contracts Missing | Section 130, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| DIR-007 | Director Consent Not Filed Within 30 Days | Section 92, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| DIR-008 | Director Holding Office of Profit Without Consent | Section 104, Companies Act 1994 (Bangladesh) | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| DIR-010 | Managing Director Appointed for More Than 5 Years | Section 110, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| ESC-001 | Strike-Off Risk Elevated | Section 346, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| ESC-002 | Strike-Off Imminent — BLACK OVERRIDE | Section 346, Companies Act 1994 (Bangladesh) | BLACK | 10 | YES | Engine-aligned 2026-11-02 |
| ESC-003 | Corporate Rescue Mandatory — Systemic Failure | Sections 81, 115, 36, 346 (aggregate), Companies Act 1994 (Bangladesh) | BLACK | 10 | YES | Engine-aligned 2026-11-02 |
| ESC-004 | Voluntary Winding Up | Section 130, Companies Act 1994 (Bangladesh) | BLACK | 30 | YES | Engine-aligned 2026-11-02 |
| ESC-005 | Investigation Order Pending | Section 104, Companies Act 1994 (Bangladesh) | RED | 20 | no | Engine-aligned 2026-11-02 |
| FX-001 | Foreign Exchange Violation | Foreign Exchange Regulation Act 1947 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| INC-001 | Memorandum and Articles Not Filed | Section 23, Companies Act 1994 (Bangladesh) | RED | 15 | no | Engine-aligned 2026-11-02 |
| INC-003 | Minimum Directors Not Appointed | Section 90(2), Companies Act 1994 (Bangladesh) | BLACK | 15 | YES | Engine-aligned 2026-11-02 |
| INC-004 | Paid-Up / Authorised Capital Mismatch — Legal Review | Section 56, Companies Act 1994 (Bangladesh), subject to review | YELLOW | 0 | no | REVIEW_REQUIRED — not a void-allotment conclusion |
| INC-005 | Encashment Certificate Missing — Foreign Shareholding | BIDA Foreign Investment Act 1980; Bangladesh Bank FDI Circular | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| INC-006 | Remittance Below Work Permit Threshold | BIDA Foreign Investment Act 1980 | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| INC-007 | Business Commenced Without Section 150 Declaration | Sections 59-60, Companies Act 1994 (Bangladesh) | RED | 10 | no | Engine-aligned 2026-11-02 |
| LBR-001 | Factory License Missing | Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026; only where an applicable Government direction covers the establishment/class | NOT_EVALUATED | 0 | no | REVIEW ONLY — Government direction and establishment class required |
| LBR-002 | Factory License Expired | Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026; licence term/renewal depends on applicable direction and licence class | NOT_EVALUATED | 0 | no | REVIEW ONLY — licence, renewal and extension evidence required |
| LBR-003 | Labour Court Order Pending | Labour Act 2006 (Bangladesh), Section 209 | RED | 15 | no | Engine-aligned 2026-11-02 |
| MEM-001 | Company Operating with Fewer than Minimum Members | Section 222, Companies Act 1994 (Bangladesh) | RED | 10 | no | Engine-aligned 2026-11-02 |
| OFF-001 | Change of Registered Office Not Filed Within 28 Days | Section 77, Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| REG-001 | Statutory Registers Incomplete | Section 34, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| REG-002 | Core Statutory Registers Missing | Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh) | RED | 10 | no | Engine-aligned 2026-11-02 |
| REG-003 | Registers Not Kept at Registered Office | Section 34(2), Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| SH-001 | Share Allotment Not Filed — Form XV | Section 151, Companies Act 1994 (Bangladesh) | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| SH-002 | Share Certificates Not Issued Within 60 Days | Section 158, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| SH-003 | Capital Increase Not Filed — Form IV | Section 56, Companies Act 1994 (Bangladesh) | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| STR-001 | Name Change Not Filed | Sections 11 and 88(1), Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| STR-002 | Object Clause Change Not Filed | Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| STR-003 | AoA Alteration Not Filed | Sections 20 and 88(1), Companies Act 1994 (Bangladesh) | YELLOW | 3 | no | Engine-aligned 2026-11-02 |
| TAX-001 | Tax Identification Number (TIN) Not Obtained | Income Tax Act 2023, Sections 166, 261 and 264; company-specific duty, identity and evidence require verification | NOT_EVALUATED | 0 | no | REVIEW ONLY — profile boolean is not proof of breach |
| TAX-002 | VAT Registration Required But Not Obtained | VAT Act 2012, as amended by Act No. 77 of 2026: BDT 30 lakh enlistment and BDT 50 lakh registration thresholds, subject to rolling 12-month taxable turnover and mandatory categories | NOT_EVALUATED | 0 | no | REVIEW ONLY — taxpayer class, activity and BIN evidence required |
| TAX-003 | Annual Tax Return Overdue | Income Tax Act 2023, Sections 170(2) and 171, as substituted by Finance Act 2026 (Act No. 96 of 2026) | NOT_EVALUATED | 0 | no | REVIEW ONLY — income-year, taxpayer class, holiday and extension checks required |
| TAX-004 | Advance Tax Missed | Income Tax Act 2023, Sections 154–157, as amended by Finance Act 2026 (Act No. 96 of 2026) | NOT_EVALUATED | 0 | no | REVIEW ONLY — liability, s.156 class, A-B computation and payment evidence required |
| TL-001 | Trade License Not Obtained | Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009 | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| TL-002 | Trade License Expired | Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009 | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| TR-001 | No Share Transfer Instrument — Form 117 | Section 38, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| TR-002 | Stamp Duty Not Paid on Share Transfer | Stamp Act 1899, Schedule I, Item 62 | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| TR-003 | No Board Approval for Share Transfer | Section 38; AoA, Companies Act 1994 (Bangladesh) | YELLOW | 8 | no | Engine-aligned 2026-11-02 |
| TR-004 | Register of Members Not Updated After Transfer | Section 34, Companies Act 1994 (Bangladesh) | YELLOW | 5 | no | Engine-aligned 2026-11-02 |
| TR-005 | Share Transfer Violates AoA Restriction — BLACK OVERRIDE | Section 38; AoA, Companies Act 1994 (Bangladesh) | BLACK | 15 | YES | Engine-aligned 2026-11-02 |
| TR-006 | Composite Irregular Transfer | Sections 34, 47, 108, Companies Act 1994 (Bangladesh) | RED | 10 | no | Engine-aligned 2026-11-02 |
| VAT-002 | Monthly VAT Return Overdue | VAT Act 2012, Section 64, as substituted by VAT Amendment Ordinance 2026 (Ordinance No. 38 of 2026, dated 14 October 2026); each tax period, 15/20-day class rules and Board extensions | NOT_EVALUATED | 0 | no | REVIEW ONLY — do not use superseded three-tax-period cycle |
| VAT-003 | VAT Annual Return Overdue | No universal annual VAT return duty identified; exact applicable Act/Rule/SRO/order must be established | NOT_EVALUATED | 0 | no | REVIEW ONLY — no automatic annual-return default |

## Module counts

| Module | Count |
|--------|-------|
| ACC | 3 |
| AGM | 7 |
| AR | 4 |
| AUD | 5 |
| BNK | 3 |
| BOD | 3 |
| BSEC | 4 |
| CAP | 4 |
| CHG | 1 |
| DEF | 2 |
| DIR | 9 |
| ESC | 5 |
| FX | 1 |
| INC | 6 |
| LBR | 3 |
| MEM | 1 |
| OFF | 1 |
| REG | 3 |
| SH | 3 |
| STR | 3 |
| TAX | 4 |
| TL | 2 |
| TR | 6 |
| VAT | 2 |
| **TOTAL** | **85** |

## Change log (matrix)

| Date | Change |
|------|--------|
| 2026-11-06 | Corrected AGM quorum, BSEC condition, labour licensing, charge satisfaction, income-tax and VAT current-law candidate anchors; provisional severities reset to NOT_EVALUATED where applicability/evidence remain unresolved. No counsel approval implied. |
| 2026-11-02 | Full rebuild from engine + seed for v2.2.0 / 85-rule corpus |
| 2026-11-02 | AUD-001: Section 210(6), one calendar month (was 210(1) / 30 days) |
| 2026-11-02 | DEF-001: Section 94 evidence-required (was Section 297) |
| 2026-11-02 | REG-002: Sec 34/89/174 internal vs Sec 115 RJSC filing |
| 2026-11-02 | Historical reconciliation notes; not a current legal approval record. See legal_approval_register.yaml. |

## Explicit non-claims

1. Engine/seed alignment is **not** primary-source legal verification.
2. Canonical architecture `RECONCILE` / `PENDING` statuses are unchanged by this matrix.
3. Deadline day-counts and practice notes still need lawyer confirmation where historically disputed.

