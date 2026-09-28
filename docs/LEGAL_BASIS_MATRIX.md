# ILRMF Legal Basis Matrix
Version: 2.1.1  
Date: 2026-09-29  
Branch: fix/legal-engine-audit-corrections

This matrix maps every active rule_id to its statutory basis as implemented in the engine.
It is a living document. Any change to a rule’s statutory_basis requires an update here.

## Core RJSC / Companies Act 1994 (Verified)

| Rule ID | Rule Name | Statutory Basis | Deadline / Trigger | Severity | Status |
|---------|-----------|-----------------|--------------------|----------|--------|
| AR-001 | Annual Return Default | Section 36 (Schedule X) | 21 days after AGM | YELLOW/RED | ✅ Verified 2026-09-29 |
| AR-002 | Annual Return 2-Year Backlog | Sections 36 + 304 | unfiled ≥ 2 | RED | ✅ Verified |
| AR-003 | Annual Return 3-Year Backlog | Sections 36 + 304 | unfiled ≥ 3 | BLACK | ✅ Verified |
| AR-004 | Annual Return Incomplete | Section 36 + Schedule X | missing attachments | YELLOW | ✅ Verified |
| AGM-001 | First AGM Default | Section 81 | 18 months (548 days) | RED/BLACK | Directionally correct |
| AGM-002 | Subsequent AGM Default | Section 81 | 15 months / FY+6m | RED/BLACK | Directionally correct |
| AGM-003 | AGM Notice Defective | Section 85 | < 21 clear days | YELLOW | Review: many firms use 14 days |
| AGM-004 | AGM Notice Missing | Section 85 | no notice | RED | Directionally correct |
| AGM-005 | AGM Quorum Not Met | Section 83 | < 2 members | RED | Directionally correct |
| AGM-006 | AGM Minutes Not Prepared | Section 83 | no minutes | YELLOW | Directionally correct |
| AGM-007 | AGM Adjourned Without Notice | Section 84 | adjourned w/o notice | YELLOW | New – needs review |
| AUD-001 | First Auditor Not Appointed | Section 210(1) | 30 days | YELLOW | Directionally correct |
| AUD-002 | Audit Missing Pre-AGM | Section 151 | audit incomplete before AGM | YELLOW/RED | Directionally correct |
| AUD-003 | AGM Held Without Valid Audit | Sections 151, 210 | AGM without audit | BLACK | Directionally correct |
| AUD-004 | Auditor Not Reappointed | Section 210(2) | not reappointed at AGM | YELLOW | Directionally correct |
| AUD-005 | Subsequent Auditor Not Appointed | Section 210(2) | no auditor for FY | RED | New – needs review |
| DIR-001–004 | Director Filing (Form XII) | Section 92 / practice | 14 days | YELLOW/RED | Citation approximate |
| DIR-005 | Register of Directors Interests | Section 97 | missing register | YELLOW | New |
| DIR-006 | Register of Contracts | Section 98 | missing register | YELLOW | New |
| INC-001–006 | Incorporation / Capital / FDI | Sections 11, 90(2), 150 + BIDA | various | YELLOW–BLACK | Core correct |
| OFF-001 | Registered Office Change | Section 81 / Form VI | 28 days | YELLOW/RED | Directionally correct |
| REG-001–003 | Statutory Registers | Sections 34, 83, 87, 90 | missing / wrong location | YELLOW–BLACK | Directionally correct |
| CAP / CHG / SH / TR | Capital, Charges, Shares, Transfers | Sections 46, 47, 50, 52, 54, 87, 100, 108 | various | YELLOW–BLACK | Directionally correct |
| ESC-001–005 | Escalation / Strike-off / Winding-up | Sections 196, 199, 297, 304 | multi-year default | RED/BLACK | Directionally correct |
| DEF-001–002 | Director Disqualification / Penalties | Sections 297, 447 | disqualified / unresolved | YELLOW/BLACK | New |
| TL-001–002 | Trade Licence | City Corp / Pourashava | missing / expired | YELLOW | Advisory |
| TAX-001–004 / VAT-002–003 | Tax & VAT | ITA 2023, VAT Act 2012 | various | YELLOW/RED | Advisory |
| BSEC-001–004 | BSEC CG Code | BSEC CG Code 2023 | listed only | YELLOW/RED | Conditional / Advisory |
| BNK-001–003 | Insolvency | Bankruptcy Act 1997 | petition / liquidator / court | BLACK | Advisory |
| LBR-001–003 | Labour | Labour Act 2006 | factory licence / court | YELLOW/RED | Advisory |
| FX-001 | Foreign Exchange | FE Regulation Act 1947 | violation flag | RED | Advisory |
| STR-001–003 | Structural Changes | Sections 17, 18, 20 | name / objects / AoA | YELLOW/RED | Directionally correct |

## Notes
- **Verified** = cross-checked against Companies Act 1994 text and current RJSC practice (2026-09-29).
- **Directionally correct** = section and logic align with common practice; exact wording/deadlines should be confirmed by counsel.
- **Advisory** = outside pure RJSC core; useful for scoring but should be labelled as secondary in UI.
- AGM notice period (AGM-003) remains at 21 clear days pending counsel confirmation (many firms use 14).

## Change Control
Any modification to a rule’s statutory_basis, deadline, or severity must update this matrix and increment the matrix version.
