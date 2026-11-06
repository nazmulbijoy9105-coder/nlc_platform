# NLC Bangladesh Companies Law Master Rulebook

**Version:** 1.0.0 (Counsel Validation Draft)  
**Prepared:** 4 November 2026  
**Jurisdiction:** Bangladesh  
**Status:** DRAFT — NOT COUNSEL-VALIDATED — NOT APPROVED FOR AUTONOMOUS COMMERCIAL LEGAL DETERMINATIONS  
**Owner:** Neum Lex Counsel / NLC  
**Scope:** 85 rules currently represented in the NLC rule catalogue. This is not a claim that the whole of Bangladesh company law has been exhaustively codified.

## 1. Purpose and legal status

This is the master review baseline for independent validation by a Bangladesh senior company-law counsel. It inventories the currently implemented NLC rule catalogue and establishes the legal, evidential, temporal and governance requirements each rule must satisfy before activation.

**Critical distinction:** engine/seed parity is a software consistency check, not proof of legal correctness. A passing unit test proves only that code behaves as tested. Neither proves that the cited provision is current, applicable, correctly interpreted or properly applied to a particular company.

No rule in this draft is represented as approved by counsel. Existing engine severities, score impacts and override flags are recorded as implementation metadata only. They are not legal consequences and must not be presented as such.

## 2. Primary-source hierarchy

1. Bangladesh Laws (Ministry of Law, Justice and Parliamentary Affairs), official consolidated text of the Companies Act 1994: https://bdlaws.minlaw.gov.bd/act-print-788.html
2. Official RJSC forms and filing guidance: https://roc.gov.bd/pages/forms/6922d9b8933eb65569dffa1c and https://ebrs.roc.gov.bd/public/faqs
3. Official Gazette / amending Acts, Ordinances and SROs applicable on the relevant date. The consolidated text must be checked against each amending instrument and commencement clause.
4. BSEC rules, orders and Corporate Governance Code only for entities within their scope.
5. Bangladesh Bank, BIDA, NBR, labour and local-government instruments only where the entity, transaction, sector and facts bring them into scope.
6. Court judgments, including binding appellate decisions, to resolve interpretation, validity, extensions, remedies and procedural consequences.
7. Secondary commentary is research assistance only and cannot displace primary sources.

The Companies Act official page identifies Act XVIII of 1994, dated 12 September 1994, and records commencement on 1 December 1994 by SRO 321-Law/1994. A historic PDF or a portal copy is not, by itself, proof that no later amendment applies.

## 3. Coverage and exclusions

### Included catalogue domains
Incorporation and constitutional documents; membership and share capital; directors and officers; meetings, AGM and board process; annual returns and accounts; audit; registers and records; charges; share allotment and transfer; registered office; name and constitutional changes; strike-off and winding-up indicators; tax/VAT, foreign exchange/investment, labour, trade licence and listed-company governance indicators.

### Not yet a complete legal universe
The 85-rule catalogue does not establish comprehensive coverage of every provision, rule, regulation, tax circular, sectoral licence, foreign investment condition, insolvency route, court order, beneficial ownership disclosure, data protection, competition, securities, insurance, banking, environment or employment obligation. Absence of a rule is not a finding of compliance.

### Company categories requiring separate applicability matrices
Private company limited by shares; public company limited by shares; company limited by guarantee; unlimited company; foreign company / branch; listed issuer; regulated financial institution; sector-regulated company; dormant/non-operating company; company in liquidation or winding-up; company with foreign investment. Counsel must define scope and exceptions for each.

## 4. Mandatory rule data model

Every production rule must have: stable rule_id; legal proposition; exact Act/rule/regulation/order and subsection; official source URL and source hash; amendment instrument; publication and commencement dates; effective_from/effective_to; transitional provisions; jurisdiction; entity and company-type scope; factual predicates; exclusions and exceptions; legal interpretation; burden/standard of proof where relevant; required evidence; provenance and custodian; event date and knowledge date; deadline calculation convention; extension/condonation treatment; consequence/remedy/penalty; limitation and appeal; confidence/status; reviewer and approval; tests and version.

Use bitemporal treatment: (a) legal validity period and (b) when NLC learned/recorded the source. Historical assessments must preserve the exact rule version and evidence snapshot used at that time.

## 5. Evidence and evaluation protocol

Use at least these states: VERIFIED_PRESENT; VERIFIED_ABSENT; ASSERTED; NOT_PRODUCED; REGISTRY_UNAVAILABLE; CONFLICTING; DISPUTED; STALE; NOT_APPLICABLE; UNKNOWN. Do not collapse absence of uploaded evidence into proof that a document does not exist. Identify source, issuer, document ID, execution date, effective date, receipt date, custodian, hash, chain of custody, authentication method, reviewer and contradiction links.

A statutory deadline is not a guessed number of days. Store the event that starts time, statutory unit (calendar days/months/years/working days), exclusion/inclusion rules, holidays if legally relevant, extension authority, actual extension order, due date, filing channel and proof of receipt. Calendar month must not be silently converted to 30 days.

## 6. Legal and product safeguards

- UNKNOWN, disputed, missing or inaccessible evidence must not be automatically treated as a proven breach.
- Do not automatically invalidate an AGM, resolution, appointment, allotment or filing unless the statute/case law supports that consequence and counsel has approved the precise predicate.
- Do not create automatic BLACK status from a label, missing upload, unverified allegation or aggregate heuristic.
- Separate statutory consequence from NLC risk rating and commercial rescue priority.
- Do not state that an auditor, director or company has committed fraud without evidence and legal review.
- A rule can be activated only after counsel approval, source pinning, tests and governance approval.
- Every report must disclose the assessment date, rule version, sources, company facts, missing evidence, limitations and human reviewer.

## 7. Priority legal issues requiring counsel determination

The current-law register records open findings that must be reconciled before production. At minimum:
- DEF-001: Section 94 grounds and Articles-based additional grounds; the current five-year claim is not supported by the cited section. Section 94(1)(d) uses 180 days after the last date fixed for payment, not a generic six-month shorthand.
- AUD-001: Section 210(6) first auditor appointment uses one calendar month from registration; distinguish Board appointment from auditor's separate notice obligations.
- AUD-003/AUD-004/AUD-005: prior engine/seed/matrix entries contain conflicting or incorrect statutory anchors and unsupported automatic consequences. Section 151 concerns return of allotment, not audit. Section 210 subsections and exceptions must be separately validated.
- AGM-001/002: Section 81 deadline computation, extension powers, company-specific exceptions and calendar-month logic.
- AGM-003/004/005/006/007: notice, quorum, adjournment, minutes and Articles-dependent rules require exact provision and AoA mapping.
- ACC-001/002/003: distinguish accounts preparation, audit, laying before AGM and filing with Registrar; validate Section 181, 183 and 190 separately.
- DIR-001/002/003/007: resolve Sections 90, 92, 93 and 115 roles; Form IX consent and Form XII particulars must not be conflated.
- REG-001/002/003: separate company-maintained registers from Registrar-maintained records; Sections 34, 89, 115 and 174 require precise obligation mapping.
- CAP/CHG: distinguish charge creation, modification and satisfaction; verify Sections 159, 167, 172 and applicable forms/deadlines.
- INC-004: verify authorized capital, allotment, paid-up capital and the exact statutory mechanism; do not infer illegality solely from inconsistent database fields.
- BSEC-001..004: listed-issuer scope and applicable Code version must be established; BSEC-004 currently has an obviously suspect Foreign Exchange Regulation Act citation and must be held.
- BNK-001..003: verify whether the Bankruptcy Act is even the proper source for each winding-up event; company winding-up is principally addressed under Companies Act provisions. Do not infer winding-up from a petition label.
- TAX/VAT/FX/LBR/TL/INC-005/006: each requires separate sector-, turnover-, transaction-, employee- and effective-date applicability analysis against current NBR, Bangladesh Bank, BIDA, Labour and local-government instruments.

## 8. RJSC operational cross-checks

The official RJSC portal identifies entity types and the annual/change-return process. Its published FAQ lists, among other items, Schedule X within 21 days of AGM, balance sheet and profit-and-loss account within 30 days of AGM, Form 23B, Form IX, Form XII and incorporation documents. RJSC guidance is useful operational evidence, but counsel must reconcile each item to the current statutory text and applicable company category. The RJSC page itself may be old; check live form versions, fee rules, electronic workflow and any later SRO.

## 9. Rule catalogue (85 implemented entries)

The following is an inventory of rules present in the current legal-basis matrix, not a finding that they are valid or complete. Engine severity/score/BLACK values are included only for traceability and require separate approval.

| Rule ID | Catalogue label | Cited basis in current matrix | Engine metadata | Legal status |
|---|---|---|---|---|
| ACC-001 | Financial Statements Not Presented at AGM | Section 183, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| ACC-002 | Financial Statements Not Filed with Registrar | Section 190, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| ACC-003 | Books of Account Not Kept | Section 181, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| AGM-001 | First AGM Default | Section 81, Companies Act 1994 (Bangladesh) | RED / 20 / BLACK=false | PENDING COUNSEL |
| AGM-002 | Subsequent AGM Default | Section 81, Companies Act 1994 (Bangladesh) | RED / 20 / BLACK=false | PENDING COUNSEL |
| AGM-003 | AGM Notice Defective — Insufficient Days | Section 85, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| AGM-004 | AGM Notice Missing | Section 85, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| AGM-005 | AGM Quorum Not Met | Section 89, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| AGM-006 | AGM Minutes Not Prepared | Section 89, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| AGM-007 | AGM Adjourned Without Proper Notice | Section 130, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| AR-001 | Annual Return Default — Single Year | Section 36 (Schedule X), Companies Act 1994 (Bangladesh) | YELLOW / 10 / BLACK=false | PENDING COUNSEL |
| AR-002 | Annual Return Backlog — Review Required | Section 36 and Schedule X; Section 346 governs a separate Registrar strike-off process | NOT_EVALUATED / 0 / BLACK=false | PENDING COUNSEL — backlog alone is not a legal conclusion |
| AR-003 | Annual Return Backlog — Extended Review Required | Section 36 and Schedule X; Section 346 requires separate Registrar grounds and notice steps | NOT_EVALUATED / 0 / BLACK=false | PENDING COUNSEL — no automatic strike-off or rescue conclusion |
| AR-004 | Annual Return Filed But Incomplete | Section 36, Schedule X, Companies Act 1994 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| AUD-001 | First Auditor Not Appointed Within One Calendar Month | Section 210(6), Companies Act 1994 (Bangladesh) | YELLOW / 10 / BLACK=false | PENDING COUNSEL |
| AUD-002 | Audit Not Completed Before AGM | Section 183, Companies Act 1994 (Bangladesh) | RED / 12 / BLACK=false | PENDING COUNSEL |
| AUD-003 | AGM Held Without Completed Audit — BLACK OVERRIDE | Sections 151, 210, Companies Act 1994 (Bangladesh) | BLACK / 10 / BLACK=true | PENDING COUNSEL |
| AUD-004 | Auditor Not Reappointed at AGM | Section 210(2), Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| AUD-005 | Subsequent Auditor Not Appointed | Section 210(3), Companies Act 1994 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| BNK-001 | Winding Up Petition Filed | Bankruptcy Act 1997 (Bangladesh), Section 12 | BLACK / 10 / BLACK=true | PENDING COUNSEL |
| BNK-002 | Liquidator Appointed | Bankruptcy Act 1997 (Bangladesh), Section 14 | BLACK / 10 / BLACK=true | PENDING COUNSEL |
| BNK-003 | Court-Ordered Winding Up | Bankruptcy Act 1997 (Bangladesh), Section 18 | BLACK / 35 / BLACK=true | PENDING COUNSEL |
| BOD-001 | Board Meeting Not Held Within Quarter | Section 96, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| BOD-002 | Board Meeting Notice Not Given | Section 95, Companies Act 1994 (Bangladesh) | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| BOD-003 | Board Meeting Minutes Not Prepared | Section 89, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| BSEC-001 | BSEC Quarterly Report Not Filed | BSEC Corporate Governance Code 2023, Para 8 | RED / 10 / BLACK=false | PENDING COUNSEL |
| BSEC-002 | CG Certificate Not Obtained | BSEC Corporate Governance Code 2023, Para 5 | RED / 10 / BLACK=false | PENDING COUNSEL |
| BSEC-003 | Board Composition Non-Compliant | BSEC Corporate Governance Code 2023, Para 5 | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| BSEC-004 | Audit Committee Not Established | Foreign Exchange Regulation Act 1947 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| CAP-001 | Capital Alteration Without Proper Resolution | Section 53, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| CAP-002 | Charge Not Registered With RJSC Within 21 Days | Section 159(1), Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| CAP-003 | Capital Reduction Without Court Order | Section 150, Companies Act 1994 (Bangladesh) | BLACK / 15 / BLACK=true | PENDING COUNSEL |
| CAP-004 | Special Resolution Not Filed With RJSC | Section 88, Companies Act 1994 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| CHG-001 | Charge Satisfaction — Evidence Review Required | Section 172(1), read with Section 159, Companies Act 1994 (Bangladesh) | NOT_EVALUATED / 0 / BLACK=false | PENDING COUNSEL; registrability and filing evidence required |
| DEF-001 | Director Disqualified | Section 94, Companies Act 1994 (Bangladesh) | BLACK / 20 / BLACK=true | PENDING COUNSEL |
| DEF-002 | Unresolved Penalty Notices | Section 397, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| DIR-001 | Director Appointment Not Filed Within 14 Days | Section 90, Companies Act 1994 (Bangladesh) | YELLOW / 10 / BLACK=false | PENDING COUNSEL |
| DIR-002 | Director Departure Not Filed Within 14 Days | Section 93, Companies Act 1994 (Bangladesh) | YELLOW / 10 / BLACK=false | PENDING COUNSEL |
| DIR-003 | Major Director Filing Irregularity — Over 1 Year | Section 115, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| DIR-004 | Departed Director Still Active on RJSC Register | Section 109, Companies Act 1994 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| DIR-005 | Register of Directors Interests Missing | Section 130, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| DIR-006 | Register of Contracts Missing | Section 130, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| DIR-007 | Director Consent Not Filed Within 30 Days | Section 93, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| DIR-008 | Director Holding Office of Profit Without Consent | Section 104, Companies Act 1994 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| DIR-010 | Managing Director Appointed for More Than 5 Years | Section 110, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| ESC-001 | Strike-Off Process Status Requires Verification | Section 346, Companies Act 1994 (Bangladesh) | NOT_EVALUATED / 0 / BLACK=false | PENDING COUNSEL — verify statutory notice sequence |
| ESC-002 | Strike-Off Status Requires Verification | Section 346, Companies Act 1994 (Bangladesh) | NOT_EVALUATED / 0 / BLACK=false | PENDING COUNSEL — no backlog-based BLACK override |
| ESC-003 | Corporate Rescue Mandatory — Systemic Failure | NLC internal risk policy; not a statutory Companies Act consequence | BLACK / 10 / BLACK=true | POLICY OWNER APPROVAL PENDING — internal policy only |
| ESC-004 | Voluntary Winding Up | Section 130, Companies Act 1994 (Bangladesh) | BLACK / 30 / BLACK=true | PENDING COUNSEL |
| ESC-005 | Investigation Order Pending | Section 104, Companies Act 1994 (Bangladesh) | RED / 20 / BLACK=false | PENDING COUNSEL |
| FX-001 | Foreign Exchange Violation | Foreign Exchange Regulation Act 1947 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| INC-001 | Memorandum and Articles Not Filed | Section 23, Companies Act 1994 (Bangladesh) | RED / 15 / BLACK=false | PENDING COUNSEL |
| INC-003 | Minimum Directors Not Appointed | Section 90(2), Companies Act 1994 (Bangladesh) | BLACK / 15 / BLACK=true | PENDING COUNSEL |
| INC-004 | Paid-Up Capital Exceeds Authorized Capital | Section 53, Companies Act 1994 (Bangladesh) | BLACK / 20 / BLACK=true | PENDING COUNSEL |
| INC-005 | Encashment Certificate Missing — Foreign Shareholding | BIDA Foreign Investment Act 1980; Bangladesh Bank FDI Circular | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| INC-006 | Remittance Below Work Permit Threshold | BIDA Foreign Investment Act 1980 | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| INC-007 | Business Commenced Without Section 150 Declaration | Section 150, Companies Act 1994 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| LBR-001 | Factory License Missing | Labour Act 2006 (Bangladesh), Section 35 | RED / 10 / BLACK=false | PENDING COUNSEL |
| LBR-002 | Factory License Expired | Labour Act 2006 (Bangladesh), Section 35 | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| LBR-003 | Labour Court Order Pending | Labour Act 2006 (Bangladesh), Section 209 | RED / 15 / BLACK=false | PENDING COUNSEL |
| MEM-001 | Company Operating with Fewer than Minimum Members | Section 222, Companies Act 1994 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| OFF-001 | Change of Registered Office Not Filed Within 28 Days | Section 77, Companies Act 1994 (Bangladesh) | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| REG-001 | Statutory Registers Incomplete | Section 34, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| REG-002 | Core Statutory Registers Missing | Sections 34, 89, 115, 174, Companies Act 1994 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| REG-003 | Registers Not Kept at Registered Office | Section 34(2), Companies Act 1994 (Bangladesh) | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| SH-001 | Share Allotment Not Filed — Form XV | Section 151, Companies Act 1994 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| SH-002 | Share Certificates Not Issued Within 60 Days | Section 158, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| SH-003 | Capital Increase Not Filed — Form IV | Section 56, Companies Act 1994 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| STR-001 | Name Change Not Filed | Section 20, Companies Act 1994 (Bangladesh) | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| STR-002 | Object Clause Change Not Filed | Section 17, Companies Act 1994 (Bangladesh) | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| STR-003 | AoA Alteration Not Filed | Section 18, Companies Act 1994 (Bangladesh) | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| TAX-001 | Tax Identification Number (TIN) Not Obtained | Income Tax Act 2023 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| TAX-002 | VAT / turnover-tax status — review only | VAT & SD Act 2012, ss.2(48), 2(57), 4 and 10; Act 77/2026 and Finance Act 96/2026 | NOT_EVALUATED / 0 / BLACK=false | PENDING COUNSEL; no automatic breach finding |
| TAX-003 | Annual Tax Return Overdue | Income Tax Act 2023, Section 75 | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| TAX-004 | Advance Tax Missed | Income Tax Act 2023, Section 74 | YELLOW / 3 / BLACK=false | PENDING COUNSEL |
| TL-001 | Trade License Not Obtained | Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009 | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| TL-002 | Trade License Expired | Local Government (City Corporation) Act 2009 / Local Government (Paurashava) Act 2009 | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| TR-001 | No Share Transfer Instrument — Form 117 | Section 38, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| TR-002 | Stamp Duty Not Paid on Share Transfer | Stamp Act 1899, Schedule I, Item 62 | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| TR-003 | No Board Approval for Share Transfer | Section 38; AoA, Companies Act 1994 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| TR-004 | Register of Members Not Updated After Transfer | Section 34, Companies Act 1994 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |
| TR-005 | Share Transfer Violates AoA Restriction — BLACK OVERRIDE | Section 38; AoA, Companies Act 1994 (Bangladesh) | BLACK / 15 / BLACK=true | PENDING COUNSEL |
| TR-006 | Composite Irregular Transfer | Sections 34, 47, 108, Companies Act 1994 (Bangladesh) | RED / 10 / BLACK=false | PENDING COUNSEL |
| VAT-002 | Monthly VAT Return Overdue | Value Added Tax Act 2012 (Bangladesh) | YELLOW / 8 / BLACK=false | PENDING COUNSEL |
| VAT-003 | VAT Annual Return Overdue | Value Added Tax Act 2012 (Bangladesh) | YELLOW / 5 / BLACK=false | PENDING COUNSEL |

## 10. Counsel validation workflow

For every rule, counsel must:
1. Confirm exact official provision and subsection in Bangla and any official English text.
2. Identify every amendment, repeal, substitution, SRO, Ordinance and commencement provision up to the assessment date.
3. Record legal effective date and transitional treatment.
4. Confirm company category, listing/regulatory status, sector and exclusions.
5. Review the company's actual Memorandum and Articles, shareholder agreements, court orders, RJSC records and transaction documents.
6. State the legal proposition, exceptions, consequences and uncertainty.
7. Approve factual predicates and evidence sufficiency.
8. Review deadline arithmetic, extensions, condonation and limitation.
9. Approve or reject score/severity/override as NLC policy, separately from statutory law.
10. Sign the rule record and supporting memorandum; assign next review date.
11. Approve test cases and expected outcomes independently of the implementation.
12. Record conflicts, dissent and unresolved issues; unresolved rules remain NOT_EVALUATED.

## 11. Counsel sign-off sheet

For each rule: Rule ID: ______; provision: ______; amendment history checked through: ______; effective date: ______; company type: ______; Articles checked: Yes/No; facts/evidence reviewed: ______; exceptions: ______; legal consequence: ______; NLC rating approved: Yes/No; test cases approved: Yes/No; status: VALIDATED / VALIDATED_WITH_LIMITS / REJECTED / NOT_EVALUATED; counsel name, enrolment/chamber: ______; signature/date: ______; next review: ______.

## 12. Version control and release gates

Draft 1.0.0 is an inventory and validation framework. It is not a legal opinion and must not be used as the sole basis for filing, declaring default, issuing a BLACK status, making representations to investors/lenders, or advising a client.

Release gates: (1) primary-source pinning complete; (2) amendment/effective-date register complete; (3) company-type and AoA applicability complete; (4) evidence model approved; (5) every rule signed by counsel; (6) independent legal test corpus passes; (7) engine/seed/database parity passes; (8) migration and historical-version tests pass; (9) report disclosures approved; (10) governance owner authorises activation.

## 13. Sources consulted

- Bangladesh Laws, Companies Act 1994 (Act XVIII of 1994): https://bdlaws.minlaw.gov.bd/act-print-788.html
- RJSC, company and trade-organisation forms: https://roc.gov.bd/pages/forms/6922d9b8933eb65569dffa1c
- RJSC e-BRS FAQs, entity types and filing guidance: https://ebrs.roc.gov.bd/public/faqs
- RJSC business process brief: https://app.roc.gov.bd/Guidlines/RJSC_bus_pro_RF.htm
- RJSC return-filing guidance: https://roc.gov.bd/pages/static-pages/6922dbbc933eb65569e0c2d5

**Source limitation:** This draft was prepared from the NLC repository's current rule matrix and current-law correctness register plus the official sources above. It has not completed a section-by-section amendment audit through the Gazette, nor reviewed any individual company's Articles or facts. It is deliberately labelled for counsel validation.
