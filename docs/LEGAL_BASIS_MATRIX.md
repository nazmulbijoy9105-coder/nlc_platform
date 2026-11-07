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
| ACC-001 | Financial Statements Not Presented at AGM | Section 183, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| ACC-002 | Financial Statements Not Filed with Registrar | Section 190, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| ACC-003 | Books of Account Not Kept | Section 181, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AGM-001 | First AGM Default | Section 81, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AGM-002 | Subsequent AGM Default | Section 81, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AGM-003 | AGM Notice Defective — Insufficient Days | Section 85, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AGM-004 | AGM Notice Missing | Section 85, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AGM-005 | AGM Quorum Not Met | Section 85(2)(b), Companies Act 1994 (Bangladesh), subject to the company’s Articles | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — verify Articles, member count and attendance evidence |
| AGM-006 | AGM Minutes Not Prepared | Section 89, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AGM-007 | AGM Adjourned Without Proper Notice | Section 85 and applicable Articles; exact adjournment provision requires counsel mapping | NOT_EVALUATED | 0 | no | REVIEW ONLY — no automatic default |
| AR-001 | Annual Return Default — Single Year | Section 36 (Schedule X), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AR-002 | Annual Return Backlog — Review Required | Section 36 and Schedule X; Section 346 governs a separate Registrar strike-off process | NOT_EVALUATED | 0 | no | REVIEW ONLY — backlog alone is not proof of strike-off or director liability |
| AR-003 | Annual Return Backlog — Extended Review Required | Section 36 and Schedule X; Section 346 requires separate Registrar grounds and notice steps | NOT_EVALUATED | 0 | no | REVIEW ONLY — no automatic strike-off, dissolution or rescue conclusion |
| AR-004 | Annual Return Filed But Incomplete | Section 36, Schedule X, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AUD-001 | First Auditor Not Appointed Within One Calendar Month | Section 210(6), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AUD-002 | Audit Not Completed Before AGM | Section 183, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| AUD-003 | AGM Audit Status Requires Legal Review | Section 183, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Audit/account evidence and legal consequences require case-specific review; no automatic BLACK override |
| AUD-004 | Auditor Reappointment Requires Legal Review | Section 210(3), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Verify statutory exceptions and notice requirements before determining non-compliance |
| AUD-005 | Subsequent Auditor Reappointment Status Unknown | Section 210(3), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Evidence-status only; no 120-day deadline; exceptions require legal review |
| BNK-001 | Winding Up Petition Filed — Companies Act route verification | Companies Act 1994, Part V, sections 241–244; exact petition provision and case status require review | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| BNK-002 | Liquidator Appointment — route verification | Companies Act 1994, Part V; section 255 for court-appointed Official Liquidators; voluntary route requires separate mapping | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| BNK-003 | Court-Ordered Winding Up — authenticated order verification | Companies Act 1994, Part V, sections 241–246; exact order and status require review | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| BOD-001 | Board Meeting History Requires Verification | Section 96, Companies Act 1994 (Bangladesh) — at least one meeting every three months and four per year | NOT_EVALUATED | 0 | no | REVIEW ONLY — full verified meeting history required; no breach inferred from a single date |
| BOD-002 | Board Meeting Notice Status Requires Verification | Section 95, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | REVIEW ONLY — verify notice to each director then in Bangladesh and service evidence |
| BOD-003 | Board Minutes Status Requires Verification | Section 89, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | REVIEW ONLY — verify minute book and custody; missing upload is not proof of non-creation |
| BSEC-001 | BSEC Quarterly Report Not Filed | Applicable BSEC listing/securities reporting instrument; exact rule, issuer class, period and due date unresolved (not CG Code Condition 8) | NOT_EVALUATED | 0 | no | REVIEW ONLY — listed issuer scope and instrument required |
| BSEC-002 | CG Certificate Not Obtained | BSEC Corporate Governance Code 2018, Condition 9, as amended; listed-issuer scope only | NOT_EVALUATED | 0 | no | REVIEW ONLY — certifier, AGM appointment and evidence required |
| BSEC-003 | Board Composition Non-Compliant | BSEC Corporate Governance Code 2018, Condition 1, as amended; listed-issuer scope only | NOT_EVALUATED | 0 | no | REVIEW ONLY — current amendment and director eligibility required |
| BSEC-004 | Audit Committee Not Established | BSEC Corporate Governance Code 2018, Condition 5, as amended; listed-issuer scope only | NOT_EVALUATED | 0 | no | REVIEW ONLY — committee composition and duties required |
| CAP-001 | Capital Alteration Authority Review | Sections 53, 54 and 56, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| CAP-002 | Charge Not Registered With RJSC Within 21 Days | Section 159(1), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| CAP-003 | Capital Reduction Without Court Order | Sections 59-60, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| CAP-004 | Special Resolution Not Filed With RJSC within 15 days | Section 88(1), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| CHG-001 | Charge satisfaction — evidence review only | Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | Require verified s.159 registrability, satisfaction date and RJSC filing-status evidence; no inference from missing data |
| DEF-001 | Director Disqualified | Section 94, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DEF-002 | Unresolved Penalty Notices | Case-specific enabling provision; no universal section | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DIR-001 | Director Appointment Particulars Not Filed Within 14 Days | Section 115, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DIR-002 | Director Cessation Particulars Not Filed Within 14 Days | Section 115, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DIR-003 | Major Director Filing Irregularity — Over 1 Year | Section 115, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DIR-004 | Departed Director Still Active on RJSC Register | Section 109, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DIR-005 | Director Interest Disclosure/Register Requires Review | Section 130, Companies Act 1994 (Bangladesh) — disclosure of interest in contracts/arrangements, not a generic register duty | NOT_EVALUATED | 0 | no | REVIEW ONLY — rule title/trigger and any separate register duty require legal reconciliation |
| DIR-006 | Register of Contracts Requires Review | Companies Act 1994 and applicable Articles — exact provision not established | NOT_EVALUATED | 0 | no | REVIEW ONLY — no universal register duty assumed |
| DIR-007 | Director Consent Not Filed Within 30 Days | Section 93(2), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| DIR-008 | Office of Profit Status Requires Verification | Section 104, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | REVIEW ONLY — statutory exclusions and general-meeting consent must be checked |
| DIR-010 | Managing Director Term Requires Verification | Section 110, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | REVIEW ONLY — verify current appointment term, reappointment and continuity |
| ESC-001 | Strike-Off Process Status Requires Verification | Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required | NOT_EVALUATED | 0 | no | REVIEW ONLY — backlog is not proof of Registrar strike-off action |
| ESC-002 | Strike-Off Status Requires Verification | Section 346, Companies Act 1994 (Bangladesh); Registrar process and case-specific evidence required | NOT_EVALUATED | 0 | no | REVIEW ONLY — filing backlog or unverified list indicator is not proof of strike-off |
| ESC-003 | Corporate Rescue Mandatory — Systemic Failure | NLC internal risk policy; not a statutory Companies Act consequence | NOT_EVALUATED | 0 | no | POLICY OWNER APPROVAL PENDING — no statutory BLACK classification |
| ESC-004 | Voluntary Winding Up | Section 286 and following provisions, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| ESC-005 | Investigation Appointment — evidence review only | Sections 195 and 197; section 199 where related entities are included, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| FX-001 | Foreign Exchange Violation | Foreign Exchange Regulation Act 1947 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| INC-001 | Memorandum and Articles Not Filed | Section 23, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| INC-003 | Minimum Directors Not Appointed | Section 90(2), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| INC-004 | Paid-Up / Authorised Capital Mismatch — Legal Review | Section 56, Companies Act 1994 (Bangladesh), subject to review | NOT_EVALUATED | 0 | no | REVIEW_REQUIRED — not a void-allotment conclusion |
| INC-005 | Encashment Certificate Missing — Foreign Shareholding | BIDA Foreign Investment Act 1980; Bangladesh Bank FDI Circular | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| INC-006 | Remittance Below Work Permit Threshold | BIDA Foreign Investment Act 1980 | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| INC-007 | Section 150 Commencement Declaration — limited applicability review | Section 150(1) and (6), Companies Act 1994 (Bangladesh); private companies and companies not issuing a public-subscription prospectus are excluded | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| LBR-001 | Factory License Missing | Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026; only where an applicable Government direction covers the establishment/class | NOT_EVALUATED | 0 | no | REVIEW ONLY — Government direction and establishment class required |
| LBR-002 | Factory License Expired | Bangladesh Labour Act 2006, Section 326, as amended by Act No. 43 of 2026; licence term/renewal depends on applicable direction and licence class | NOT_EVALUATED | 0 | no | REVIEW ONLY — licence, renewal and extension evidence required |
| LBR-003 | Labour Court Order Pending | Labour Act 2006 (Bangladesh), Section 209 | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| MEM-001 | Company Operating with Fewer than Minimum Members | Section 222, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| OFF-001 | Change of Registered Office Not Filed Within 28 Days | Section 77, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| REG-001 | Statutory Registers Incomplete | Section 34, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| REG-002 | Core Statutory Registers Missing | Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| REG-003 | Registers Not Kept at Registered Office | Section 34(2), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| SH-001 | Share Allotment Not Filed — Form XV | Section 151, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| SH-002 | Share Certificates Not Issued Within 90 Days | Section 158, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| SH-003 | Capital Increase Not Filed — Form IV | Section 56, Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| STR-001 | Name Change Not Filed | Sections 11 and 88(1), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| STR-002 | Object Clause Change Not Filed | Sections 12, 15-16 and 88(1), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| STR-003 | AoA Alteration Not Filed | Sections 20 and 88(1), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TAX-001 | Tax Identification Number (TIN) Not Obtained | Income Tax Act 2023, Sections 166, 261 and 264; company-specific duty, identity and evidence require verification | NOT_EVALUATED | 0 | no | REVIEW ONLY — profile boolean is not proof of breach |
| TAX-002 | VAT registration / turnover-tax enlistment status — review only | VAT & SD Act 2012, ss.2(48), 2(57), 4 and 10; Act 77/2026 and Finance Act 96/2026. BDT 30 lakh enlistment / BDT 50 lakh registration thresholds; statutory 12-month turnover, exclusions and s.4(2) categories govern | NOT_EVALUATED | 0 | no | REVIEW ONLY — no breach finding from annual-turnover estimate; taxpayer-specific evidence and counsel review required |
| TAX-003 | Annual Tax Return Overdue | Income Tax Act 2023, Sections 170(2) and 171, as substituted by Finance Act 2026 (Act No. 96 of 2026) | NOT_EVALUATED | 0 | no | REVIEW ONLY — income-year, taxpayer class, holiday and extension checks required |
| TAX-004 | Advance Tax Missed | Income Tax Act 2023, Sections 154–157, as amended by Finance Act 2026 (Act No. 96 of 2026) | NOT_EVALUATED | 0 | no | REVIEW ONLY — liability, s.156 class, A-B computation and payment evidence required |
| TL-001 | Trade License Not Obtained | Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009 | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TL-002 | Trade License Expired | Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009 | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TR-001 | Share Transfer Instrument — Section 38(3) Evidence Review | Section 38(3), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TR-002 | Stamp Duty Not Paid on Share Transfer | Stamp Act 1899, Schedule I, Item 62 | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TR-003 | Articles-Based Transfer Restriction Review | Section 38(7), Companies Act 1994 (Bangladesh); Articles of Association | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TR-004 | Notice of Refusal to Register Transfer | Section 38(4), Companies Act 1994 (Bangladesh) | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TR-005 | Registered Transfer Despite Articles Restriction — Counsel Review | Section 38(7), Companies Act 1994 (Bangladesh); Articles of Association | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
| TR-006 | Composite Transfer Record Review | Sections 34 and 38, Companies Act 1994 (Bangladesh), and applicable Articles | NOT_EVALUATED | 0 | no | INTERNAL TRIAGE — NOT COUNSEL APPROVED |
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

## Primary source links and legal provenance

These are primary/official source entry points used for this limited correction pass. They do not replace a consolidated amendment history, commencement analysis, company-specific applicability review or signed counsel approval.

- Companies Act 1994 (official BDLaws): https://bdlaws.minlaw.gov.bd/act-print-788.html
- Companies Act 1994, section 85 (official BDLaws): https://bdlaws.minlaw.gov.bd/act-print-788/section-print-32909.html
- Companies Act 1994, section 172 (official BDLaws): https://bdlaws.minlaw.gov.bd/act-788/act-part-print-355.html
- BSEC Corporate Governance Code, Gazette notification dated 3 June 2018 (official BSEC PDF): https://www.sec.gov.bd/slaws/Corporate_Governance_Code_10.06.2018.pdf
- Income Tax Act 2023 and Finance Act 2026 (official BDLaws): https://bdlaws.minlaw.gov.bd/act-print-1725.html
- VAT Amendment Act 2026, Act No. 77 of 2026 (official BDLaws): https://bdlaws.minlaw.gov.bd/act-print-1706.html
- VAT Amendment Ordinance 2026, Ordinance No. 38 of 2026, section 64 substitution (official BDLaws): https://bdlaws.minlaw.gov.bd/act-1742/section-59742.html
- Bangladesh Labour (Amendment) Act 2026, Act No. 43 of 2026 (official BDLaws): https://bdlaws.minlaw.gov.bd/act-print-1672.html
- DIFE official laws register: https://dife.gov.bd/pages/laws

**Temporal caution:** VAT Ordinance No. 38 of 2026 is dated 14 October 2026 and replaces section 64 with filing per tax period (subject to 15/20-day class rules, holidays and Board extension). Do not use the superseded three-tax-period formulation from the Finance Act 2026 alone. The 2026 VAT Amendment Act No. 77 and Ordinance No. 38 are distinct instruments with different subject matter.

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

